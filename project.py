from openerp import tools
from openerp.osv import fields, osv
from openerp.addons.project import project
from openerp.addons.project_issue import project_issue
from openerp.addons.base_status.base_stage import base_stage
from openerp.tools.translate import _
from datetime import *
import sys
from PyQt4.QtCore import *
import easygui as e

class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'
    
    def project_create(self, cr, uid, analytic_account_id, vals, context=None):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically linked to it if the conditions are meet.
        '''
        project_pool = self.pool.get('project.project')
        project_id = project_pool.search(cr, uid, [('analytic_account_id','=', analytic_account_id)])
        if not project_id and self._trigger_project_creation(cr, uid, vals, context=context):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': analytic_account_id,
                'type': vals.get('type','contract'),
            }
            project_id =  project_pool.create(cr, uid, project_values, context=context)
            return project_id
        return project_id

    def create(self, cr, uid, vals, context=None):
            if context is None:
                context = {}
            if vals.get('child_ids', False) and context.get('analytic_project_copy', False):
                vals['child_ids'] = []
            analytic_account_id = super(account_analytic_account, self).create(cr, uid, vals, context=context)
            project_id = self.project_create(cr, uid, analytic_account_id, vals, context=context)
            if project_id:
                list_id = []
                list_id.append(project_id);
                self.pool.get('project.project').dispatch_mail(cr,uid,project_id,context)
            return analytic_account_id
 
class project_issue(base_stage,osv.osv):
    _name = 'project.issue'
    _inherit = ['project.issue','mail.thread','ir.needaction_mixin']
    _description = "Adding Mail Functionality"

    def create(self,cr,uid,vals,context=None):
        if context is None:
            context = {}
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        create_context = dict(context, mail_create_nolog=True)
        id = super(project_issue,self).create(cr,uid,vals,context)
        if vals.get('is_send_mail',False) == True:
            context.update({'project_issue_custom_module':True})
            result = self.dispatch_mail(cr,uid,id,context)
            if result == False:
                print("No mail was dispatched to the employee probably due to configuration problems\n1. E-mail ID for the employee is missing\n2. The 'Assigned To' field in the issue form is missing", "Error")
        return id
    
    def dispatch_mail(self,cr,uid,id,context):
        try:
            info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
            if type(id) == type([]): id = id[0]
            if context == None: context = {}
            context.update({'lang':str(info.get('lang',False) or ''),
                            'tz':str(info.get('tz',False) or ''),
                            'active_ids':[id],
                            'active_id':id,
                            'uid':uid,
                            'active_model':'project.issue',
                            }) 
            ir_model_data = self.pool.get('ir.model.data') 
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management_employee_issue')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = context
            ctx.update({
                'default_model': 'project.issue',
                'default_res_id': id,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',  
                'compose_form_id':compose_form_id,
                'custom_module':True,
            })
            context = ctx
            wizard_object = self.pool.get('mail.compose.message')
            brw_obj = self.browse(cr,uid,id,context)
            if brw_obj.user_id and brw_obj.user_id.email:
                mail_employee = brw_obj.user_id.partner_id.id
                wizard_id = wizard_object.create(cr,uid,{'partner_ids':[(4,mail_employee)],
                                                                                 'template_id':template_id,
                                                                                  'composition_mode':'comment',
                                                                                  'res_id':id,
                                                                                  },context)
                values = wizard_object.onchange_template_id(cr, uid, id, template_id,'comment','project.issue',id, context=None)
                wizard_object.write(cr,uid,wizard_id,values['value'],context)
                ctx.update({
                            'wizard_id':wizard_id,
                            })
                wizard_id_list = []
                wizard_id_list.append(wizard_id) 
                wizard_object.send_mail(cr,uid,wizard_id_list,context)
                return True
            else:
                return False
        except:
            return False                
    
    _defaults = {
                 'is_send_mail':True,
                 }
    _columns = {
                'is_send_mail':fields.boolean('Dispatch mail after Issue Creation'),
                }
class project_project(osv.osv):
    _inherit = "project.project"
    _description = "Adding Email Functionality"
    
    def set_done(self, cr, uid, ids, context=None):
        task_obj = self.pool.get('project.task')
        task_ids = task_obj.search(cr, uid, [('project_id', 'in', ids), ('state', 'not in', ('cancelled', 'done'))])
        info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
        if type(ids) == type([]): id = ids[0]
        if context == None: context = {}
        context.update({'lang':str(info.get('lang',False) or ''),
                        'tz':str(info.get('tz',False) or ''),
                        'active_ids':[id],
                        'active_id':id,
                        'uid':uid,
                        'active_model':'project.project',
                        }) 
        ir_model_data = self.pool.get('ir.model.data') 
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management_project_close_message')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = context
        ctx.update({
            'default_model': 'project.project',
            'default_res_id': id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'mass_mail',  
            'compose_form_id':compose_form_id,
            'custom_module':True,
        })
        context = ctx
        wizard_object = self.pool.get('mail.compose.message')
        brw_obj = self.browse(cr,uid,id,context)
        if brw_obj.partner_id:
            mail_customer = brw_obj.partner_id.id
            wizard_id = wizard_object.create(cr,uid,{'partner_ids':[(4,mail_customer)],
                                                                             'template_id':template_id,
                                                                              'composition_mode':'mass_mail',
                                                                              'res_id':id
                                                                              },context)
            values = wizard_object.onchange_template_id(cr, uid, id, template_id,'comment','project.project',id, context=None)
            wizard_object.write(cr,uid,wizard_id,values['value'],context)
            ctx.update({
                        'wizard_id':wizard_id,
                        })
            wizard_id_list = []
            wizard_id_list.append(wizard_id) 
            wizard_object.send_mail(cr,uid,wizard_id_list,context)
        else:
            print("No mail was dispatched because the project does not have any customer", "Error")
        task_obj.case_close(cr, uid, task_ids, context=context)
        return self.write(cr, uid, ids, {'state':'close'}, context=context)

    def dispatch_mail(self,cr,uid,id,context):
        try:
            info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
            if type(id) == type([]): id = id[0]
            if context == None: context = {}
            context.update({'lang':str(info.get('lang',False) or ''),
                            'tz':str(info.get('tz',False) or ''),
                            'active_ids':[id],
                            'active_id':id,
                            'uid':uid,
                            'active_model':'project.project',
                            }) 
            ir_model_data = self.pool.get('ir.model.data') 
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management_customer_project')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = context
            ctx.update({
                'default_model': 'project.project',
                'default_res_id': id,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',  
                'compose_form_id':compose_form_id,
                'custom_module':True,
            })
            context = ctx
            wizard_object = self.pool.get('mail.compose.message')
            brw_obj = self.browse(cr,uid,id,context)
            if brw_obj.partner_id and brw_obj.partner_id.email:
                mail_customer = brw_obj.partner_id.id
                wizard_id = wizard_object.create(cr,uid,{'partner_ids':[(4,mail_customer)],
                                                                                 'template_id':template_id,
                                                                                  'composition_mode':'mass_mail',
                                                                                  'res_id':id
                                                                                  },context)
                values = wizard_object.onchange_template_id(cr, uid, id, template_id,'comment','project.project',id, context=None)
                wizard_object.write(cr,uid,wizard_id,values['value'],context)
                ctx.update({
                            'wizard_id':wizard_id,
                            })
                wizard_id_list = []
                wizard_id_list.append(wizard_id) 
                wizard_object.send_mail(cr,uid,wizard_id_list,context)
            else:
                return False
        except:
            return False                
        
    def check_user(self,cr,uid,id,context):
        obj = self.pool.get('res.users')
        print obj.read(cr,uid,uid,['group_ids'],context)
        return True
       
    def _progress_rate(self, cr, uid, ids, names, arg, context=None):
        uid = 1
        child_parent = self._get_project_and_children(cr, uid, ids, context)
        # compute planned_hours, total_hours, effective_hours specific to each project
        cr.execute("""
            SELECT project_id, COALESCE(SUM(planned_hours), 0.0),
                COALESCE(SUM(total_hours), 0.0), COALESCE(SUM(effective_hours), 0.0)
            FROM project_task WHERE project_id IN %s AND state <> 'cancelled'
            GROUP BY project_id
            """, (tuple(child_parent.keys()),))
        # aggregate results into res
        res = dict([(id, {'planned_hours':0.0,'total_hours':0.0,'effective_hours':0.0}) for id in ids])
        for id, planned, total, effective in cr.fetchall():
            # add the values specific to id to all parent projects of id in the result
            while id:
                if id in ids:
                    res[id]['planned_hours'] += planned
                    res[id]['total_hours'] += total
                    res[id]['effective_hours'] += effective
                id = child_parent[id]
        # compute progress rates
        for id in ids:
            project_task_obj = self.pool.get('project.task')
            #Total tasks of the current project
            list_task_project = project_task_obj.search(cr,uid,[('project_id','=',id)],offset=0, limit=None, order=None, context=context, count=False)
            list_task_project_done = project_task_obj.search(cr,uid,[('project_id','=',id),('state','=','done')],offset=0, limit=None, order=None, context=context, count=False)
            try:
                res[id]['progress_rate'] = round((float(len(list_task_project_done))/len(list_task_project))*100, 2)
            except ZeroDivisionError:
                res[id]['progress_rate'] = 0.0
        for id in ids:
            if res[id]['effective_hours'] > res[id]['planned_hours']:
                self.write(cr,uid,id,{'color':2},context)
        return res

    def create(self,cr,uid,vals,context=None):
        
        self.check_user(cr, uid, uid, context)
        id = super(project.project_project,self).create(cr,uid,vals,context)
        if vals.get('is_send_mail',False) == True:
            context.update({'project_custom_module':True})
            result = self.dispatch_mail(cr,uid,id,context)
            if result == False:
                print("No mail was dispatched to the customer probably due to configuration problems\n1. E-mail ID for the customer is missing\n2. The customer field in the project form is missing", "Error")
        return id
    

    _defaults = {
                 'is_send_mail':True,
                 'privacy_visibility':'public',
                 }
    _columns = {
                'total_hours': fields.function(_progress_rate, multi="progress", string='Total Time', help="Sum of total hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (
                    lambda project_obj, cr,uid, ids, context=None: project_obj._get_project_and_parents(cr, uid, ids, context),
                    ['tasks', 'parent_id', 'child_ids'],
                    10),
                #task_obj is a replacement of self for better understanding
                'project.task': (lambda task_obj, cr, uid, ids, context=None : task_obj.pool.get('project.project')._get_projects_from_tasks(cr, uid, ids, context),
                                 ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 
                                 20),
            }),
                'progress_rate': fields.function(_progress_rate, multi="progress", string='Progress', type='float', group_operator="avg", help="Percent of tasks closed according to the total of tasks todo.",
            store = {
                'project.project': (
                    lambda project_obj, cr, uid, ids, context=None: project_obj._get_project_and_parents(cr, uid, ids, context),
                    ['tasks', 'parent_id', 'child_ids'],
                    10),
                #task_obj is a replacement of self for better understanding
                'project.task': (lambda task_obj, cr, uid, ids, context=None : task_obj.pool.get('project.project')._get_projects_from_tasks(cr, uid, ids, context),
                                 ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 
                                 20),
            }),

                'planned_hours': fields.function(_progress_rate, multi="progress", string='Planned Time', help="Sum of planned hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (
                    lambda project_obj, cr, uid, ids, context=None: project_obj._get_project_and_parents(cr, uid, ids, context),
                    ['tasks', 'parent_id', 'child_ids'],
                    10),
                #task_obj is a replacement of self for better understanding
                'project.task': (lambda task_obj, cr, uid, ids, context=None : task_obj.pool.get('project.project')._get_projects_from_tasks(cr, uid, ids, context),
                                 ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 
                                 20),
            }),

                'effective_hours': fields.function(_progress_rate, multi="progress", string='Time Spent', help="Sum of spent hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (
                    lambda project_obj, cr, uid, ids, context=None: project_obj._get_project_and_parents(cr, uid, ids, context),
                    ['tasks', 'parent_id', 'child_ids'],
                    10),
                #task_obj is a replacement of self for better understanding
                'project.task': (lambda task_obj, cr, uid, ids, context=None : task_obj.pool.get('project.project')._get_projects_from_tasks(cr, uid, ids, context),
                                 ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 
                                 20),
            }),

                'is_send_mail':fields.boolean('Dispatch Mail After Project Creation ?'),
                }
    
        
class mail_compose_message(osv.TransientModel):
    _inherit = 'mail.compose.message'
    _description = 'Template Onchange Functionality'
    
    def onchange_template_id(self, cr, uid, ids, template_id, composition_mode, model, res_id, context=None):
    
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values """
        values = {}
        if context == None:context={}
        if template_id and composition_mode == 'mass_mail' and context.get('custom_module',False) == False:
            values = self.pool.get('email.template').read(cr, uid, template_id, ['subject', 'body_html', 'attachment_ids'], context)
            values.pop('id')
        elif template_id:
            if context.get('custom_module',False):
                values = self.generate_email_for_composer(cr, uid, template_id, res_id, context=context)
                # transform attachments into attachment_ids; not attached to the document because this will
                # be done further in the posting process, allowing to clean database if email not send
                values['attachment_ids'] = values.pop('attachment_ids', [])
                ir_attach_obj = self.pool.get('ir.attachment')
                for attach_fname, attach_datas in values.pop('attachments', []):
                    data_attach = {
                        'name': attach_fname,
                        'datas': attach_datas,
                        'datas_fname': attach_fname,
                        'res_model': 'mail.compose.message',
                        'partner_id':False,
                        'res_id': 0,
                        'type': 'binary',  # override default_type from context, possibly meant for another model!
                    }
                    values['attachment_ids'].append(ir_attach_obj.create(cr, uid, data_attach, context=context))
                partner_id = self.read(cr,uid,ids[0],['partner_ids'],context)
                values.update({'partner_ids':partner_id['partner_ids']})
            else:
                values = self.generate_email_for_composer(cr, uid, template_id, res_id, context=context)
                # transform attachments into attachment_ids; not attached to the document because this will
                # be done further in the posting process, allowing to clean database if email not send
                values['attachment_ids'] = values.pop('attachment_ids', [])
                ir_attach_obj = self.pool.get('ir.attachment')
                for attach_fname, attach_datas in values.pop('attachments', []):
                    data_attach = {
                        'name': attach_fname,
                        'datas': attach_datas,
                        'datas_fname': attach_fname,
                        'res_model': 'mail.compose.message',
                        'partner_id':False,
                        'res_id': 0,
                        'type': 'binary',  # override default_type from context, possibly meant for another model!
                    }
                    values['attachment_ids'].append(ir_attach_obj.create(cr, uid, data_attach, context=context))
        else:
            values = self.default_get(cr, uid, ['body', 'subject', 'partner_ids', 'attachment_ids'], context=context)

        if values.get('body_html'):
            values['body'] = values.pop('body_html')
        return {'value': values}
    
class project_task_work(osv.osv):
    _inherit = 'project.task.work'
    
    def unlink(self, cr, uid, ids, context=None):
        toremove = {}
        record_id = self.browse(cr, uid, ids, context=context)
        for i in record_id:
            if i.recorder_id:
                self.pool.get('project.task.time.recorder').unlink(cr, uid, i.recorder_id.id, context=context)
        super(project_task_work, self).unlink(cr, uid, ids, context=context)
        return True
    
    _columns = {
                'recorder_id':fields.many2one('project.task.time.recorder')
                }

class project_task_time_recorder(osv.osv):
    _name = 'project.task.time.recorder'
    _description = 'Project task Time Recorder Line'
    _defaults = {
                 'started_by':lambda self, cr, uid, context: uid,
                 }

    def check_timer_stop(self,cr,uid,context=None):
        res_val = self.pool.get('res.users').read(cr,uid,uid,['working_task','working_issue','task_name','issue_name'])
        if res_val.get('working_issue',False) and res_val.get('issue_name',False):
            list_id = []
            list_id.append(res_val.get('issue_name',False)[0])
            return {'name':res_val.get('issue_name',False)[1],
                    'type':'issue','list_id':list_id,}
        
        if res_val.get('working_task',False) and res_val.get('task_name',False):
            list_id = []
            list_id.append(res_val.get('task_name',False)[0])
            return {'name':res_val.get('task_name',False)[1],
                    'type':'task','list_id':list_id,}
        return {'type':'clear'}
    
    def close_work(self,cr,uid,context=None):
        if context.get('type',False) == 'task':
            self.pool.get('project.task.work').write(cr,uid,context.get('list_id',False),{'name':context.get('name',"Work Summary")},context)
        if context.get('type',False) == 'issue':
            self.pool.get('project.issue').write(cr,uid,context.get('list_id',False),{'name':context.get('name',"Work Summary")},context)
        return True
        
    _columns = {
                'record_task_id':fields.many2one('project.task.work',ondelete='cascade'),
                'connect':fields.many2one('project.task',invisible=True),
                'start_time':fields.datetime('Start Time'),
                'stop_time':fields.datetime('Stop Time'),
                'difference_time':fields.related('record_task_id','hours',type="float",string = 'Effective Hours Worked'),
                'started_by':fields.many2one('res.users','Started By'),
                }

class project_task(base_stage, osv.osv):
    _inherit = 'project.task'
    _description = "Project Task Management"
    
    def action_close(self, cr, uid, ids, context=None):
        """ This action closes the task
        """
        task_id = len(ids) and ids[0] or False
        self._check_child_task(cr, uid, ids, context=context)
        if not task_id: return False
        info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
        if type(ids) == type([]): id = ids[0]
        if context == None: context = {}
        context.update({'lang':str(info.get('lang',False) or ''),
                        'tz':str(info.get('tz',False) or ''),
                        'active_ids':[id],
                        'active_id':id,
                        'uid':uid,
                        'active_model':'project.task',
                        }) 
        ir_model_data = self.pool.get('ir.model.data') 
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management_task_close_message')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = context
        ctx.update({
            'default_model': 'project.task',
            'default_res_id': id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'mass_mail',  
            'compose_form_id':compose_form_id,
            'custom_module':True,
        })
        context = ctx
        wizard_object = self.pool.get('mail.compose.message')
        brw_obj = self.browse(cr,uid,id,context)
        
        #Changes made @Karolis request
        
        if brw_obj.project_id :
            if brw_obj.project_id.partner_id:
                mail_customer = brw_obj.project_id.partner_id.id
                wizard_id = wizard_object.create(cr,uid,{'partner_ids':[(4,mail_customer)],
                                                                                 'template_id':template_id,
                                                                                  'composition_mode':'mass_mail',
                                                                                  'res_id':id
                                                                                  },context)
                values = wizard_object.onchange_template_id(cr, uid, id, template_id,'comment','project.task',id, context=None)
                wizard_object.write(cr,uid,wizard_id,values['value'],context)
                ctx.update({
                            'wizard_id':wizard_id,
                            })
                wizard_id_list = []
                wizard_id_list.append(wizard_id) 
                wizard_object.send_mail(cr,uid,wizard_id_list,context)
            else:
               print ("No mail was dispatched because the project does not have any customer", "Error")
        else:
            print ("No mail was dispatched because no project was mentioned on the task", "Error")
        return self.do_close(cr, uid, [task_id], context=context)
    
    def check_work_summary(self,cr,uid,ids,context):
        for id in ids:
            total = 0.00
            brw_obj =self.browse(cr,uid,id,context)
            for j in brw_obj.timer_lines:
                if j.difference_time:
                    total+= j.difference_time
        nid = self.pool.get('wizard.calculate.timer').create(cr,uid,{'total_time':total},context)
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_id':nid,
                'res_model': 'wizard.calculate.timer',
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    def desc_pop_start(self,cr,uid,id,context):
        ir_model_data = self.pool.get('ir.model.data')
        if context.get('source',False) == "javascript":
            view_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'description_pop_view_signout')[1]
        else:
            view_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'description_pop_view_start')[1]
        employee_obj = self.pool.get('hr.employee')
        flag = 0
        user_working_obj = self.pool.get('res.users')
        user_working = user_working_obj.read(cr,uid,uid,['working_task','task_name','working_issue','issue_name'],context)
        if user_working.get('working_task',False):
            if user_working.get('task_name',False):
                list_id = []
                list_id.append(user_working.get('task_name',False)[0])
                context.update({'list_id':list_id,'source':'project.task'})
                wizard_id = self.pool.get('description.pop').create(cr,uid,{
                                                                'work_name':user_working.get('task_name',False)[1],
                                                                'type':'task'
                                                                },context)
                return {
                        'view_type': 'form',
                        "view_mode": 'form',
                        'res_model': 'description.pop',
                        'type': 'ir.actions.act_window',
                        'res_id':wizard_id,
                        'view_id' : view_id,
                        'target': 'new',
                        'context':context
                       }                        
            else:
                raise osv.except_osv(('Warning'), ('The Existing task on which the user is working is not known. Please fill it in the user form'))
        elif user_working.get('issue_name',False):
            if user_working.get('issue_name',False):
                list_id = []
                list_id.append(user_working.get('issue_name',False)[0])
                context.update({'list_id':list_id,'source':'project.issue'})
                wizard_id = self.pool.get('description.pop').create(cr,uid,{
                                                                'work_name':user_working.get('issue_name',False)[1],
                                                                'type':'issue'
                                                                },context)                
                return {
                        'view_type': 'form',
                        "view_mode": 'form',
                        'res_model': 'description.pop',
                        'type': 'ir.actions.act_window',
                        'view_id' : view_id,
                        'res_id':wizard_id,
                        'target': 'new',
                        'context':context
                       }                                        
            else:
                raise osv.except_osv(('Warning'), ('The Existing Issue on which the user is working is not known. Please fill it in the user form'))
        else:
            self.timer_state_start(cr,uid,id,context)
        return True

    def timer_state_start(self,cr,uid,id,context):
        if context==None: context = {}
        flag = 0
        user_working_obj = self.pool.get('res.users')
        employee_obj = self.pool.get('hr.employee')
        employee_id = employee_obj.search(cr,uid,[],offset=0, limit=None, order=None, context=None, count=False)
        for employee in employee_id:
            brw_obj = employee_obj.browse(cr,uid,employee,context)
            if brw_obj.user_id.id == uid:
                if brw_obj.state == 'present':
                    clock_state = self.read(cr,uid,id[0],['timer_state','last_work_summary_added_id','user_id'],context)
                    if not clock_state.get('user_id',False):
                        raise osv.except_osv(('Warning'), ('You cannot start a task before a user is assigned to it'))
                    if str(clock_state.get('timer_state','stop')) == 'stop' or clock_state.get('timer_state','stop') == False :
                        flag = 1
                        nid = self.pool.get('project.task.time.recorder').create(cr,uid,{
                                                                                    'start_time':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                                                    'connect':id[0],
                                                                                        },context)
                        self.write(cr,uid,id,{'timer_state':'start','last_work_summary_added_id':nid,'user_start':uid},context)
                        user_working_obj.write(cr,uid,uid,{'working_task':True,
                                                           'task_name':id[0],
                                                           },context)

        if flag == 0:            
            raise osv.except_osv(('Warning'), (' Either you have not Signed In or you are not related to any employee'))
        return True
    
    def desc_pop_stop(self,cr,uid,id,context):
        ir_model_data = self.pool.get('ir.model.data')
        view_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'description_pop_view')[1]
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'description.pop',
                'type': 'ir.actions.act_window',
                'view_id' : view_id,
                'target': 'new',
                               
               }
        
    def timer_state_stop(self,cr,uid,id,context):
        if context==None: context = {}
        work_obj = self.pool.get('project.task.work')
        clock_state = self.read(cr,uid,id[0],['timer_state','last_work_summary_added_id'],context)
        user_start = self.read(cr,uid,id[0],['user_start'],context)
        user_working_obj = self.pool.get('res.users')
        user_working = user_working_obj.read(cr,uid,user_start.get('user_start',1)[0],['working_task'],context)
        if user_working.get('working_task',False):
            user_working_obj.write(cr,uid,user_start.get('user_start',1)[0],{'working_task':False,
                                               'task_name':False,
                                               },context)
        if str(clock_state.get('timer_state','start')) == 'start' :
            same_employee = self.pool.get('project.task.time.recorder').read(cr,uid,clock_state.get('last_work_summary_added_id',1),['started_by'],context)
            if same_employee.get('started_by',1)[0] == uid :
                timer_obj = self.pool.get('project.task.time.recorder')
                timer_lines_info = timer_obj.browse(cr,uid,clock_state.get('last_work_summary_added_id',1),context)
                stop_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                stop_time_datetime = datetime.strptime(stop_time, "%Y-%m-%d %H:%M:%S")
                start_time_datetime =  datetime.strptime(timer_lines_info.start_time, "%Y-%m-%d %H:%M:%S")
                difference_time  = stop_time_datetime - start_time_datetime
                difference_time_float = difference_time.days*24 +  float(difference_time.seconds)/3600
                task_work_id = work_obj.create(cr,uid,{ 'task_id':id[0],  
                                          'name':context.get('desc','Work Summary'),
                                          'hours':difference_time_float,
                                          'date':stop_time,
                                          'user_id':uid, 
                                          'recorder_id':clock_state.get('last_work_summary_added_id',1)         
                                        },context)
                timer_obj.write(cr,uid,clock_state.get('last_work_summary_added_id',1),{'stop_time':stop_time,'record_task_id':task_work_id},context)
                self.write(cr,uid,id,{'timer_state':'stop'},context)
            else:
                raise osv.except_osv(('Warning'), ('The Employee who has started the task can close the task'))
        return  True
        
    def assign_me(self,cr,uid,id,context):
        user_id = self.read(cr,uid,id[0],['user_id'],context)
        self.write(cr,uid,id[0],{'user_id':uid},context)
        context.update({'assign_me':True})
        self.create_mail(cr,uid,id,context=context)
        mail_employee = [] 
        manager_id = self.read(cr,uid,id[0],['manager_id',],context)
        #do not get confused with the method name it is actually sending a mail to the user and the manager only
        message_follower_ids = []
        message_follower_ids.append(uid)
        message_follower_ids.append(manager_id.get('manager_id',1)[0])
        set(message_follower_ids)
        mail_employee = []
        for employees in message_follower_ids:
            partner_id = self.pool.get('res.users').read(cr,uid,employees,['partner_id'],context)
            mail_employee.append(partner_id.get('partner_id',False)[0])
        set(mail_employee)
        self.write(cr,uid,id,{'message_follower_ids':[(6,0,mail_employee)]},context)
        return True
            
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
#if choice is department then first make user_id = False and the people belonging to the department to message_follower_ids
        mail_employee = []
        if vals.get('partner_id',False):
            mail_employee.append(vals.get('partner_id',False))
        if vals.get('assign_to_choice',False) == 'department':
            vals['user_id'] = False
            if vals.get('department_id',False):
                employee_obj = self.pool.get('hr.employee')
                employee_ids = employee_obj.search(cr,uid,[],offset=0, limit=None, order=None, context=None, count=False)
                for i in employee_ids:
                    hr_info = employee_obj.read(cr,uid,i,['department_id','user_id'],context)
                    try:
                        dept_id = hr_info.get('department_id',False)[0]
                    except TypeError:
                        continue
                    if dept_id == vals['department_id']:
                        if hr_info.get('user_id'):
                            partner_id = self.pool.get('res.users').read(cr,uid,hr_info.get('user_id')[0],['partner_id'],context)
                            mail_employee.append(partner_id['partner_id'][0])
                set(mail_employee)
        else:
            vals['department_id'] = False
            partner_id = self.pool.get('res.users').read(cr,uid,vals['user_id'],['partner_id'],context)
            mail_employee.append(partner_id['partner_id'][0])
            set(mail_employee)
        vals['message_follower_ids'] = mail_employee
        task_id = super(project.task, self).create(cr, uid, vals, context=create_context)
        self._store_history(cr, uid, [task_id], context=context)
        self.customer_mail(cr,uid,task_id,context)
        return task_id

    # Overridden to reset the kanban_state to normal whenever
    # the stage (stage_id) of the task changes.
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('stage_id',False):
            for id in ids:
                timer_state = self.read(cr,uid,id,['timer_state','stage_id'],context)
                if timer_state.get('timer_state',False) == "start":
                    state_state = self.pool.get('project.task.type').read(cr,uid,vals.get('stage_id',False),['state'],context)
                    if state_state.get('state',False) == 'done':
                        raise osv.except_osv(('Error'), ('The task can be closed only once the timer is stopped'))
        
        if vals.get('timer_state',False) :
            for id in ids:
                timer_state = self.read(cr,uid,id,['stage_id'],context)
                if vals.get('timer_state',False) == 'start':
                    if vals.get('stage_id',False) :state_state = self.pool.get('project.task.type').read(cr,uid,vals.get('stage_id',False),['state'],context)
                    else:state_state = self.pool.get('project.task.type').read(cr,uid,timer_state.get('stage_id',False)[0],['state'],context)
                    if state_state.get('state',False) == 'done':
                            raise osv.except_osv(('Error'), ('The closed task timer cannot be started'))                        
                        
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals and not 'kanban_state' in vals and 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for t in self.browse(cr, uid, ids, context=context):
                #TO FIX:Kanban view doesn't raise warning
                #stages = [stage.id for stage in t.project_id.type_ids]
                #if new_stage not in stages:
                #raise osv.except_osv(_('Warning!'), _('Stage is not defined in the project.'))
                write_vals = vals_reset_kstate if t.stage_id != new_stage else vals
                super(project.task, self).write(cr, uid, [t.id], write_vals, context=context)
            result = True
        else:
            result = super(project.task, self).write(cr, uid, ids, vals, context=context)
        if ('stage_id' in vals) or ('remaining_hours' in vals) or ('user_id' in vals) or ('state' in vals) or ('kanban_state' in vals):
            self._store_history(cr, uid, ids, context=context)
        return result

    def customer_mail(self,cr,uid,id,context=None):
        info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
        if type(id) == type([]): id = id[0]
        if context == None: context = {}
        context.update({'lang':str(info.get('lang',False) or ''),
                        'tz':str(info.get('tz',False) or ''),
                        'active_ids':[id],
                        'active_id':id,
                        'uid':uid,
                        'active_model':'project.task',
                        }) 
        ir_model_data = self.pool.get('ir.model.data') 
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management_customer')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = context
        ctx.update({
            'default_model': 'project.task',
            'default_res_id': id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'mass_mail',  
            'compose_form_id':compose_form_id,
            'custom_module':True,
        })
        context = ctx
        wizard_object = self.pool.get('mail.compose.message')
        brw_obj = self.browse(cr,uid,id,context)
        if brw_obj.project_id :
            if brw_obj.project_id.partner_id:
                mail_customer = brw_obj.project_id.partner_id.id
                wizard_id = wizard_object.create(cr,uid,{'partner_ids':[(4,mail_customer)],
                                                                                 'template_id':template_id,
                                                                                  'composition_mode':'mass_mail',
                                                                                  'res_id':id
                                                                                  },context)
                values = wizard_object.onchange_template_id(cr, uid, id, template_id,'comment','project.task',id, context=None)
                wizard_object.write(cr,uid,wizard_id,values['value'],context)
                ctx.update({
                            'wizard_id':wizard_id,
                            })
                wizard_id_list = []
                wizard_id_list.append(wizard_id) 
                wizard_object.send_mail(cr,uid,wizard_id_list,context)
                return True
            else:
                return False
        else:
            return False

    def create_mail(self,cr,uid,id,context=None):
        info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
        if type(id) == type([]): id = id[0]
        if context == None: context = {}
        context.update({'lang':str(info.get('lang',False) or ''),
                        'tz':str(info.get('tz',False) or ''),
                        'active_ids':[id],
                        'active_id':id,
                        'uid':uid,
                        'active_model':'project.task',
                        })  
        try:
            vals = self.read(cr,uid,id,['department_id','assign_to_choice','user_id','manager_id'],context)
            manager_id = self.pool.get('res.users').browse(cr,uid,vals.get('manager_id',1)[0],context).partner_id.id
            customer_id = 0
            if vals.get('partner_id',False):
                customer_id = vals.get('partner_id',1)[0]
            if vals['department_id'] != False:
                department_id = vals['department_id'][0]
            else:
                department_id = False
            mail_employee = []
            employee_obj = self.pool.get('hr.employee')
            if str(vals.get('assign_to_choice',False)) == 'department' and vals.get('user_id',False) == False:
                employee_ids = employee_obj.search(cr,uid,[],offset=0, limit=None, order=None, context=None, count=False)
                for i in employee_ids:
                    hr_info = employee_obj.read(cr,uid,i,['department_id','user_id'],context)
                    try:
                        dept_id = hr_info.get('department_id',False)[0]
                    except TypeError:
                        continue
                    if dept_id == department_id:
                        if hr_info.get('user_id'):
                            partner_id = self.pool.get('res.users').read(cr,uid,hr_info.get('user_id')[0],['partner_id'],context)
                            mail_employee.append(partner_id['partner_id'][0])
                    
            else:
                user_id = self.read(cr,uid,id,['user_id'],context)
                partner_id = self.pool.get('res.users').read(cr,uid,user_id['user_id'][0],['partner_id'],context)
                mail_employee.append(partner_id['partner_id'][0])
            ir_model_data = self.pool.get('ir.model.data')
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = context
            ctx.update({
                'default_model': 'project.task',
                'default_res_id': id,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'mass_mail',  
                'compose_form_id':compose_form_id,
                'custom_module':True,
            })
            context = ctx
            mail_employee = set(mail_employee)
            mail_employee = list(mail_employee)
            wizard_id = self.pool.get('mail.compose.message').create(cr,uid,{'partner_ids':[(6,0,mail_employee)],
                                                                             'template_id':template_id,
                                                                              'composition_mode':'mass_mail',
                                                                              'res_id':id,
                                                                              },context)
            values = self.pool.get('mail.compose.message').onchange_template_id(cr, uid, id, template_id,'comment','project.task',id, context=None)
            self.pool.get('mail.compose.message').write(cr,uid,wizard_id,values['value'],context)
            ctx.update({
                        'wizard_id':wizard_id,
                        })
            
            if context.get('assign_me',False):
                wizard_id_list = []
                wizard_id_list.append(wizard_id) 
                self.pool.get('mail.compose.message').send_mail(cr,uid,wizard_id_list,context)
                return True
                
            if context.get('button',False):
                return {
                     'type': 'ir.actions.act_window',
                     'view_type': 'form',
                     'res_id':wizard_id,
                     'view_mode': 'form',
                     'res_model': 'mail.compose.message',
                     'views': [(compose_form_id, 'form')],
                     'view_id': compose_form_id,
                     'target': 'new',
                     'context':ctx,
                   }
            else:
                return ctx
    #             mail_vals = {
    #                          'partner_ids':mail_employee,
    #                          'template_id':3,
    #                          'model':'project.task',
    #                          'composition_mode':'comment',
    #                          'res_id':id,
    #                          }
    #             mail_obj = self.pool.get('mail.compose.message')
        except TypeError:
            return True
    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        cr.execute("SELECT task_id, COALESCE(SUM(hours),0) FROM project_task_work WHERE task_id IN %s GROUP BY task_id",(tuple(ids),))
        hours = dict(cr.fetchall())
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = {'effective_hours': hours.get(task.id, 0.0), 'total_hours': (task.remaining_hours or 0.0) + hours.get(task.id, 0.0)}
            res[task.id]['delay_hours'] = res[task.id]['total_hours'] - task.planned_hours
            res[task.id]['progress'] = 0.0
            if (task.remaining_hours + hours.get(task.id, 0.0)):
                res[task.id]['progress'] = round(min(100.0 * hours.get(task.id, 0.0) / res[task.id]['total_hours'], 99.99),2)
            if task.state in ('done','cancelled'):
                res[task.id]['progress'] = 100.0
        for id in ids:
            hours = self.read(cr,uid,id,['planned_hours','color','effective_hours','message_follower_ids'],context)
            if hours.get('effective_hours',0) > hours.get('planned_hours',0):
                self.write(cr,uid,id,{'color':2},context)
        return res
    
    def onchange_choice(self,cr,uid,ids,assign_to_choice,id,context=None):
        if id:
            return {'value':{'department_id':False,
                             'user_id':False,
                             }}
        else:
            return {'value':{}}
        
    def onchange_department(self,cr,uid,ids,assign_to_choice,user_id,id,department_id,context=None):
        
        if assign_to_choice == 'department' and id == False:
            return {'value':{'user_id':False}}
        elif assign_to_choice == 'users' and id == False:
            return {'value':{'department_id':False}}
        elif assign_to_choice == 'users' and id != False:
            return {'value':{'department_id':False}}
        elif assign_to_choice == 'department' and id != False:
            return {'value':{}}
        return {'value':{'department_id':False,'user_id':False}}
    
    def onchange_dept_check(self,cr,uid,ids,assign_to_choice,user_id,id,department_id,context=None):
       
       if assign_to_choice == 'department' and id == False:
            return {'value':{'user_id':False}}
       elif assign_to_choice == 'users' and id == False:
            return {'value':{'department_id':False}}
       elif assign_to_choice == 'users' and id != False:
            return {'value':{'department_id':False}}
       elif assign_to_choice == 'department' and id != False:
            return {'value':{}}
       return {'value':{'department_id':False,'user_id':False}}
           
    _defaults = {
                 'user_id':False,
                 'manager_id':lambda self, cr, uid, context: uid,
                 'start_datetime':lambda *a: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 'timer_state':'stop',
                 'last_work_summary_added_id':0,
                 }
    _columns = {
                 'user_start':fields.many2one('res.users'), # this is to record the user who has started this task
                 'last_work_summary_added_id':fields.integer('Last Work Summary Line ID'), 
                'timer_lines':fields.one2many('project.task.time.recorder','connect','Time Lines'),
                'timer_state':fields.selection([
                                                ('stop','Timer Stopped'),
                                                ('start','Timer Started'),
                                                ],'Timer'),
                'start_datetime':fields.datetime('Starting Time & Date'),
                'manager_id':fields.many2one('res.users',string = 'Manager'),
                'effective_hours': fields.function(_hours_get, string='Hours Spent', multi='hours', help="Computed using the sum of the task work done.",
                    store = {
                        'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                        'project.task.work': (lambda project_task_work_obj, cr, uid, ids, context:project_task_work_obj.pool.get('project.task')._get_task( cr, uid, ids, context), 
                                              ['hours'], 10),
                    }),
                'remaining_hours': fields.float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task."),
                'total_hours': fields.function(_hours_get, string='Total', multi='hours', help="Computed as: Time Spent + Remaining Time.",
                    store = {
                        'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                        'project.task.work': (lambda project_task_work_obj, cr, uid, ids, context:project_task_work_obj.pool.get('project.task')._get_task( cr, uid, ids, context), 
                                              ['hours'], 10),
                    }),

                'progress': fields.function(_hours_get, string='Progress (%)', multi='hours', group_operator="avg", help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time",
                    store = {
                        'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                        'project.task.work': (lambda project_task_work_obj, cr, uid, ids, context:project_task_work_obj.pool.get('project.task')._get_task( cr, uid, ids, context), 
                                              ['hours'], 10),
                    }),

                'delay_hours': fields.function(_hours_get, string='Delay Hours', multi='hours', help="Computed as difference between planned hours by the project manager and the total hours of the task.",
                    store = {
                        'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                        'project.task.work': (lambda project_task_work_obj, cr, uid, ids, context:project_task_work_obj.pool.get('project.task')._get_task( cr, uid, ids, context), 
                                              ['hours'], 10),
                    }),

                'assign_to_choice':fields.selection([('users','User'),('department','Department')],
                                                    string = "Assign To User/Department"),
                'department_id':fields.many2one('hr.department','Department'),
                'user_id': fields.many2one('res.users', string='Assigned to', track_visibility='onchange'),
                }
