# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Sertek Media Project Management',
    'version' : '1.1',
    'author' : 'Shivam Goyal',
    'category' : 'Project Management',
    'description' : """
Project Management
====================================

Install the modules
1. web
2. base
3. project
4. mail
5. email_template
6. project_issue
7. hr
8. hr_attendance
9. project_gtd
10.contract_billing module or renamed as project_task_issue_billing (But did not include it in the dependency)
    """,
    
    'website': '',
    'images' : [],
    'depends' : ['web','base','project','mail','email_template','project_issue','hr','hr_attendance','project_gtd'],
    'data': ['project_view.xml',
             'edi/project_management_data.xml',
             'security/project_management_security.xml',
             'security/ir.model.access.csv',
             'wizard/wizard_calculate_time.xml',
             'portal_view.xml','res_users_view.xml',
             'project_issue_view.xml',
             'wizard/description_pop_view.xml',
             'views/project.xml',
             'analytic_view.xml'
             
             ],
    'demo': [],
    
    'test': [],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
