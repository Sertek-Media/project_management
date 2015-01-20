from openerp.osv import fields, osv

class res_users(osv.osv):
    _inherit= 'res.users'
    _description="Task Status"
    defaults = {
                'working_task':False,
                'working_issue':False,
                }
    _columns = {
                'working_task':fields.boolean("is Working on Task"),
                'task_name':fields.many2one('project.task','Working on Task'),
                'working_issue':fields.boolean("is Working on Issue"),
                'issue_name':fields.many2one('project.issue','Working on Issue'),
                }