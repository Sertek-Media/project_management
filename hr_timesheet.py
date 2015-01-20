from openerp.osv import osv, fields

class hr_analytic_timesheet(osv.osv):
    _inherit = "hr.analytic.timesheet"
    _description = "Timesheet Line"

    def unlink(self, cr, uid, ids, context=None):
        obj = self.pool.get('project.task.work')
        list = obj.search(cr,uid,[('hr_analytic_timesheet_id','in',ids)],offset=0, limit=None, order=None, context=None, count=False)
        obj.unlink(cr,uid,list,context)
#         super(hr_analytic_timesheet,self).unlink(cr,uid,ids,context)
        return True