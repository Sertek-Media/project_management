from openerp.osv import fields, osv

class description_pop(osv.osv_memory):
    _name="description.pop"
    _description = "Popup for Description"
    
    def timer_state_start(self,cr,uid,id,context):
        if type(id) == type([]):
            id = id[0]
        desc= self.read(cr,uid,id,['desc'],context)
        context.update({'desc':desc.get('desc','Work Summary')})
        
        if context.get('active_model',False) == 'project.task':obj = self.pool.get('project.task')
        if context.get('active_model',False) == 'project.issue':obj = self.pool.get('project.issue')
        
        if context.get('source',False) == 'project.task':
            self.pool.get('project.task').timer_state_stop(cr,uid,context.get('list_id',False),context)
            obj.timer_state_start(cr,uid,context.get('active_ids',False),context)
            
        if context.get('source',False) == 'project.issue':
            self.pool.get('project.issue').timer_state_stop(cr,uid,context.get('list_id',False),context)
            obj.timer_state_start(cr,uid,context.get('active_ids',False),context)
        
        return {
                'type': 'ir.actions.client',
                'tag': 'reload',
        }
    
    def timer_state_stop(self,cr,uid,id,context):
        if type(id) == type([]):
            id = id[0]
        model = context.get('active_model',False)
        desc= self.read(cr,uid,id,['desc'],context)
        context.update({'desc':desc.get('desc','Work Summary')})
        if context.get('resource',False) == 'task_javascript':
            cr.execute('select "id" from "project_task_work" where "create_uid" = %s\
             order by "id" desc limit 1 ' %(uid))
            id_returned = cr.fetchone()
            if id_returned :
                self.pool.get('project.task.work').write(cr,uid,id_returned[0],{'name':desc.get('desc','Work Summary')},context)
            return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
            }
        elif context.get('resource',False) == 'issue_javascript':
            cr.execute('select "id" from "hr_analytic_timesheet" where "create_uid" = %s\
             order by "id" desc limit 1 ' %(uid))
            id_returned = cr.fetchone()
            if id_returned :
                self.pool.get('hr.analytic.timesheet').write(cr,uid,id_returned[0],{'name':desc.get('desc','Work Summary')},context)
            return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
            }                               
        else: 
            self.pool.get(model).timer_state_stop(cr,uid,context.get('active_ids',False),context)
            return True
    
    _columns = {
                'work_name':fields.char('Work Name'),
                'type':fields.selection([('task','Task'),('issue','Issue')],'Type'),
                'desc':fields.char('Work Description'),
                }