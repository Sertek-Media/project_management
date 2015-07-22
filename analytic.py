from openerp.osv import fields, osv

class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"
    
    _columns = {
                'is_send_mail':fields.boolean("Dispatch Customer Notifications",help = "If the checkbox is checked, then the mails will be dispatched to the customer")
                }