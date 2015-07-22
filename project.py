from openerp import tools
from openerp.osv import fields, osv
from openerp.addons.project import project
from openerp.addons.project_issue import project_issue
# from openerp.addons.base_status.base_stage import base_stage
from openerp.tools.translate import _
from datetime import *
import sys
# from PyQt4.QtCore import *
# import easygui as e

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
        context = dict(context)
        if context is None:
            context = dict({})
        context['is_send_mail'] = vals.get('is_send_mail',False)
        if vals.get('child_ids', False) and context.get('analytic_project_copy', False):
            vals['child_ids'] = []
        analytic_account_id = super(account_analytic_account, self).create(cr, uid, vals, context=context)
        project_id = self.project_create(cr, uid, analytic_account_id, vals, context=context)
        return analytic_account_id
    
class project_issue(osv.osv):
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
            result = self.dispatch_mail(cr,uid,id,vals.get('user_id',False),context)
            if result == False:
                print("No mail was dispatched to the employee probably due to configuration problems\n1. E-mail ID for the employee is missing\n2. The 'Assigned To' field in the issue form is missing", "Error")
        return id
    
    def dispatch_mail(self,cr,uid,id,user_id,context):
        info = self.pool.get('res.users').read(cr,uid,user_id or uid,['lang','tz'],context)
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
    
    def _check_state(self,cr,uid,obj,ctx=None):
        if obj.state == 'open':
            return False
        else:
            return True
    _track = {
                'state': {
                    # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
                    'project_management.mt_project_state': _check_state,
                },              
              }
    def set_done(self, cr, uid, ids, context=None):
        task_obj = self.pool.get('project.task')
        info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
        if type(ids) == type([]): id = ids[0]
        brw_obj = self.browse(cr,uid,id,context)
        if context == None: context = {}
        if brw_obj.is_send_mail_contract:
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
        return self.write(cr, uid, ids, {'state':'close'}, context=context)
        

    def dispatch_mail(self,cr,uid,id,context):
        if type(id) == type([]):id = id[0]
        brw_obj = self.browse(cr,uid,id,context)
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
                return True
        except:
            return False   
        return False             
        
    def check_user(self,cr,uid,id,context):
        obj = self.pool.get('res.users')
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
            list_task_project_done = project_task_obj.search(cr,uid,[('project_id','=',id),('stage_id.done_state','=',True)],offset=0, limit=None, order=None, context=context, count=False)
            try:
                res[id]['progress_rate'] = round((float(len(list_task_project_done))/len(list_task_project))*100, 2)
            except ZeroDivisionError:
                res[id]['progress_rate'] = 0.0
        for id in ids:
            if res[id]['effective_hours'] > res[id]['planned_hours']:
                self.write(cr,uid,id,{'color':2},context)
        return res

    def _progress_rate(self, cr, uid, ids, names, arg, context=None):
        child_parent = self._get_project_and_children(cr, uid, ids, context)
        # compute planned_hours, total_hours, effective_hours specific to each project
        cr.execute("""
            SELECT project_id, COALESCE(SUM(planned_hours), 0.0),
                COALESCE(SUM(total_hours), 0.0), COALESCE(SUM(effective_hours), 0.0)
            FROM project_task
            LEFT JOIN project_task_type ON project_task.stage_id = project_task_type.id
            WHERE project_task.project_id IN %s AND project_task_type.fold = False
            GROUP BY project_id
            """, (tuple(child_parent.keys()),))
        # aggregate results into res
        res = dict([(id, {'planned_hours':0.0, 'total_hours':0.0, 'effective_hours':0.0}) for id in ids])
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
            list_task_project_done = project_task_obj.search(cr,uid,[('project_id','=',id),('stage_id','=','done')],offset=0, limit=None, order=None, context=context, count=False)
            try:
                res[id]['progress_rate'] = round((float(len(list_task_project_done))/len(list_task_project))*100, 2)
            except ZeroDivisionError:
                res[id]['progress_rate'] = 0.0
        for id in ids:
            if res[id]['effective_hours'] > res[id]['planned_hours']:
                self.write(cr,uid,id,{'color':2},context)
        return res
    
    
    
    def create(self,cr,uid,vals,context=None): #shivam
        self.check_user(cr, uid, uid, context)
        if vals.get('partner_id',False):
            vals['message_follower_ids'] = [vals.get('partner_id')]
        id = super(project_project,self).create(cr,uid,vals,context)
        if (context.get('default_type',False) == 'contract' and context.get('is_send_mail',False))  or vals.get('is_send_mail',False):
            context.update({'project_custom_module':True})
            result = self.dispatch_mail(cr,uid,id,context)
            if result == False:
                print("No mail was dispatched to the customer probably due to configuration problems\n1. E-mail ID for the customer is missing\n2. The customer field in the project form is missing", "Error")
        return id
    

    _defaults = {
                 'is_send_mail':False,
                 'privacy_visibility':'public',
                 }
    _columns = {
                'is_send_mail_contract':fields.related('analytic_account_id','is_send_mail',
                                                       type="boolean",string="Send Notifications to Customer",
                                                       help="If unchecked then no mail is dispatched to the customer",
                                                       ),
                
                'state': fields.selection([('template', 'Template'),
                           ('draft','New'),
                           ('open','In Progress'),
                           ('cancelled', 'Cancelled'),
                           ('pending','Pending'),
                           ('close','Closed')],
                          'Status',track_visibility='onchange', required=True, copy=False),
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
                'record_task_id':fields.many2one('project.task.work',ondelete='cascade', required=True),
                'connect':fields.many2one('project.task',invisible=True),
                'start_time':fields.datetime('Start Time'),
                'stop_time':fields.datetime('Stop Time'),
                'difference_time':fields.related('record_task_id','hours',type="float",string = 'Effective Hours Worked'),
                'started_by':fields.many2one('res.users','Started By'),
                }

class project_task_type(osv.osv):
    _inherit = 'project.task.type'
    _columns = {
                'done_state':fields.boolean('Done State')
                }
    
class project_task( osv.osv):
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
        brw_obj = self.browse(cr,uid,id,context)
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
        
        #Changes made @Karolis request
        if brw_obj.project_id and brw_obj.project_id.is_send_mail_contract:
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
        
        return True
    
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
        elif vals.get('project_id',False):
            partner_id_read = self.pool.get('project.project').read(cr,uid,vals.get('project_id'),['partner_id'],context)
            if partner_id_read.get('partner_id'):
                mail_employee.append(partner_id_read.get('partner_id',False)[0])                
        if vals.get('assign_to_choice',False) == 'department':
            vals['user_id'] = False
            if vals.get('department_id',False):
                dept_manager = self.pool.get('hr.department').browse(cr,uid,vals.get('department_id',False),context)
                if dept_manager.manager_id and dept_manager.manager_id.user_id and dept_manager.manager_id.user_id.partner_id:
                    mail_employee.append(dept_manager.manager_id.user_id.partner_id.id)
        else:
            vals['department_id'] = False
            partner_id = self.pool.get('res.users').read(cr,uid,vals['user_id'],['partner_id'],context)
            if partner_id:
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
                state_state = self.pool.get('project.task.type').read(cr,uid,vals.get('stage_id',False),['fold','done_state'],context)
                timer_state = self.read(cr,uid,id,['timer_state','stage_id'],context)
                if timer_state.get('timer_state',False) == "start":
                    if state_state.get('fold',False):
                        raise osv.except_osv(('Error'), ('A task can be folded only once the timer is stopped'))
                if state_state.get('done_state',False):
                    self.action_close(cr,uid,[id],context)
                    
                ## Enter another else condition that calls a function to sent eh msg to the customer
        if vals.get('timer_state',False) :
            for id in ids:
                timer_state = self.read(cr,uid,id,['stage_id'],context)
                if vals.get('timer_state',False) == 'start':
                    if vals.get('stage_id',False) :state_state = self.pool.get('project.task.type').read(cr,uid,vals.get('stage_id',False),['fold'],context)
                    else:state_state = self.pool.get('project.task.type').read(cr,uid,timer_state.get('stage_id',False)[0],['fold'],context)
                    if state_state.get('fold',False) :
                            raise osv.except_osv(('Error'), ('The folded task timer cannot be restarted'))                        
                        
        return super(project_task,self).write(cr,uid,ids,vals,context=context)
    
    def customer_mail(self,cr,uid,id,context=None):
        brw_obj = self.browse(cr,uid,id,context)
        #send mail only if the sending notifications to customer is allowed
        if brw_obj.project_id.is_send_mail_contract:
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
            department_id = False
            
            if vals.get('department_id',False):
                department_id = vals.get('department_id')[0]
            
            mail_employee = []
            employee_obj = self.pool.get('hr.employee')
            if str(vals.get('assign_to_choice',False)) == 'department' and vals.get('user_id',False) == False:
                dept_obj = self.pool.get('hr.department').browse(cr,uid,department_id,context)
                if dept_obj.manager_id and dept_obj.manager_id.user_id:
                    mail_employee.append(dept_obj.manager_id.user_id.partner_id.id)  
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
                                                                             'notify':False,
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
#Changed the _hours_get method with the new odoo method
    
    
    def onchange_choice(self,cr,uid,ids,assign_to_choice,context=None):
        if ids:
            return {'value':{'department_id':False,
                             'user_id':False,
                             }}
        else:
            return {'value':{}}
        
    def onchange_department(self,cr,uid,ids,assign_to_choice,user_id,department_id,context=None):
        
        if assign_to_choice == 'department' and ids == False:
            return {'value':{'user_id':False}}
        elif assign_to_choice == 'users' and ids == False:
            return {'value':{'department_id':False}}
        elif assign_to_choice == 'users' and id != False:
            return {'value':{'department_id':False}}
        elif assign_to_choice == 'department' and ids != False:
            return {'value':{}}
        return {'value':{'department_id':False,'user_id':False}}
    
    def onchange_dept_check(self,cr,uid,ids,assign_to_choice,user_id,department_id,context=None):
       
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

                'assign_to_choice':fields.selection([('users','User'),('department','Department')],
                                                    string = "Assign To User/Department"),
                'department_id':fields.many2one('hr.department','Department'),
                'user_id': fields.many2one('res.users', string='Assigned to', track_visibility='onchange'),
                }
