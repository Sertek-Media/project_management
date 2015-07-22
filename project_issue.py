from openerp.osv import fields, osv
from datetime import *
from datetime import date
# from PyQt4.QtCore import *
# import easygui as e
import time
from openerp.tools.translate import _
from openerp.addons.project_issue import project_issue
from openerp import SUPERUSER_ID

class project_task_time_recorder(osv.osv):
    _name = 'project.issue.time.recorder'
    _description = 'Project issue Time Recorder Line'
    _defaults = {
                 'started_by':lambda self, cr, uid, context: uid,
                 }

    _columns = {
                'connect':fields.many2one('project.issue',invisible=True),
                'start_time':fields.datetime('Start Time'),
                'stop_time':fields.datetime('Stop Time'),
                'difference_time':fields.float('Effective Hours Worked'),
                'started_by':fields.many2one('res.users','Started By'),
                }

class project_issue(osv.osv):
    _inherit = "project.issue"
    _description = "Portal Issue default user"

    def write(self,cr,uid,ids,vals,context=None):
        if vals.get('stage_id'):
            done_state = self.pool.get('project.task.type').read(cr,uid,vals['stage_id'],['done_state'],context)
            if done_state.get('done_state',False):
                self.case_close(cr,uid,ids,context)
        return super(project_issue,self).write(cr,uid,ids,vals,context)
        
    def case_close(self,cr,uid,ids,context=None):
        if type(ids) == type([]): id = ids[0]
        brw_obj = self.browse(cr,uid,SUPERUSER_ID,context)
        if brw_obj.project_id and brw_obj.project_id.is_send_mail_contract:
            if context == None: context = {}
            info = self.pool.get('res.users').read(cr,uid,uid,['lang','tz'],context)
            context.update({'lang':str(info.get('lang',False) or ''),
                            'tz':str(info.get('tz',False) or ''),
                            'active_uid':id,
                            'uid':uid,
                            'active_model':'project.issue',
                            }) 
            ir_model_data = self.pool.get('ir.model.data') 
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'project_management', 'email_template_edi_project_management_issue_close_message')[1]
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
            if brw_obj.project_id :
                if brw_obj.project_id.partner_id:
                    mail_customer = brw_obj.project_id.partner_id.id
                    wizard_id = wizard_object.create(cr,uid,{'partner_ids':[(4,mail_customer)],
                                                                                     'template_id':template_id,
                                                                                      'composition_mode':'comment',
                                                                                      'res_id':id
                                                                                      },context)
                    values = wizard_object.onchange_template_id(cr, uid, id, template_id,'comment','project.issue',id, context=None)
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
                print ("No mail was dispatched because no project was mentioned on the issue", "Error")
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
        clock_state = self.read(cr,uid,id[0],['timer_state','last_work_summary_added_id','project_id','analytic_account_id','type_billing'],context)
        project_id = False
        analytic_account_id = False
        if clock_state.get('project_id',False):project_id =  clock_state.get('project_id',False)[0] 
        if clock_state.get('analytic_account_id',False): analytic_account_id = clock_state.get('analytic_account_id',False)[0] 
        user_start = self.read(cr,uid,id[0],['user_start'],context)
        user_working_obj = self.pool.get('res.users')
        user_working = user_working_obj.read(cr,uid,user_start.get('user_start',1)[0],['working_issue'],context)
        if user_working.get('working_issue',False):
            user_working_obj.write(cr,uid,user_start.get('user_start',1)[0],{'working_issue':False,
                                               'issue_name':False,
                                               },context)
        if str(clock_state.get('timer_state','start')) == 'start' :
            same_employee = self.pool.get('project.issue.time.recorder').read(cr,uid,clock_state.get('last_work_summary_added_id',1),['started_by'],context)
            if same_employee.get('started_by',1)[0] == uid or uid == 1 :
                timer_obj = self.pool.get('project.issue.time.recorder')
                timer_lines_info = timer_obj.browse(cr,uid,clock_state.get('last_work_summary_added_id',1),context)
                stop_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                stop_time_datetime = datetime.strptime(stop_time, "%Y-%m-%d %H:%M:%S")
                start_time_datetime =  datetime.strptime(timer_lines_info.start_time, "%Y-%m-%d %H:%M:%S")
                difference_time  = stop_time_datetime - start_time_datetime
                difference_time_float = difference_time.days*24 +  float(difference_time.seconds)/3600
                timer_obj.write(cr,uid,clock_state.get('last_work_summary_added_id',1),{'stop_time':stop_time,'difference_time':difference_time_float},context)
                self.write(cr,uid,id,{'timer_state':'stop'},context)# this is the line
                user_start.update({'difference_time_float':difference_time_float,'project_id':project_id,
                                   'analytic_account_id':analytic_account_id,
                                   'type_billing':clock_state.get('type_billing',False)
                                   })
                return user_start
            else:
                raise osv.except_osv(('Warning'), ('The Employee who has started the issue can close the task'))
        return False
        
    def desc_pop_start(self,cr,uid,id,context):
        ir_model_data = self.pool.get('ir.model.data')
        if context.get('source',False) == "issue_javascript":
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
                        'view_id' : view_id,
                        'res_id':wizard_id,
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
        flag = 0
        if context==None: context = {}
        user_working_obj = self.pool.get('res.users')
        employee_obj = self.pool.get('hr.employee')
        employee_id = employee_obj.search(cr,uid,[],offset=0, limit=None, order=None, context=None, count=False)
        for employee in employee_id:
            brw_obj = employee_obj.browse(cr,uid,employee,context)
            if brw_obj.user_id.id == uid:
                if brw_obj.state == 'present':
                    clock_state = self.read(cr,uid,id[0],['timer_state','last_work_summary_added_id','user_id'],context)
                    if not clock_state.get('user_id',False):
                        raise osv.except_osv(('Warning'), ('You cannot start an issue before a user is assigned to it'))
                    if str(clock_state.get('timer_state','stop')) == 'stop' or clock_state.get('timer_state','stop') == False :
                        flag = 1
                        nid = self.pool.get('project.issue.time.recorder').create(cr,uid,{
                                                                                    'start_time':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                                                    'connect':id[0],
                                                                                        },context)
                        self.write(cr,uid,id,{'timer_state':'start','last_work_summary_added_id':nid,'user_start':uid},context)
                        user_working_obj.write(cr,uid,uid,{'working_issue':True,
                                                           'issue_name':id[0],
                                                           },context)
        if flag == 0:            
            raise osv.except_osv(('Warning'), (' Either you have not Signed IN or you are not related to any employee'))
        return {
    'type': 'ir.actions.client',
    'tag': 'reload',
}

    def _get_default_user(self,cr,uid,context):
        admin = 1
        if context.get('source',False) == "portal_user":
            brw = self.pool.get('res.users').browse(cr,admin,uid,context)
            if brw.partner_id.user_id:
                return brw.partner_id.user_id.id
            else:  return 1
        else: 
            return uid
        
    def _get_default_partner(self,cr,uid,context):
        admin = 1
        if context.get('source',False) == "portal_user":
            brw = self.pool.get('res.users').browse(cr,admin,uid,context)
            if brw.partner_id:
                return brw.partner_id.id
            else:  return False
        else: 
            return False
        
    _columns = {
                'user_start':fields.many2one('res.users'), # this is to record the user who has started this task
                'last_work_summary_added_id':fields.integer('Last Work Summary Line ID'), 
                'timer_lines':fields.one2many('project.issue.time.recorder','connect','Time Lines'),
                'timer_state':fields.selection([
                                                ('stop','Timer Stopped'),
                                                ('start','Timer Started'),
                                                ],'Timer'),
                }    
    
    _defaults = {
                 'user_id':_get_default_user,
                 'timer_state':'stop',
                 'partner_id':_get_default_partner,
                 }
    
