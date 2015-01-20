from openerp.osv import fields, osv

class wizard_calculate_timer(osv.osv_memory):
    _name="wizard.calculate.timer"
    _description = "Displays the total work summary"
    _columns = {
                'total_time':fields.float('Time Summary'),
                }