from odoo.tests.common import TransactionCase, HttpCase, tagged
from odoo.tools import mute_logger
from odoo.exceptions import MissingError
from odoo import Command
from psycopg2.errors import ForeignKeyViolation


class TestTaskTemplateCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user_group_employee = cls.env.ref('base.group_user')
        user_group_project_user = cls.env.ref('project.group_project_user')
        user_group_project_manager = cls.env.ref('project.group_project_manager')
        user_group_sales_manager = cls.env.ref('sales_team.group_sale_manager')
        user_group_sales_user = cls.env.ref('sales_team.group_sale_salesman')
        user_product_customer = cls.env.ref('customer_product_code.group_product_customer_code_user')

        group_ids = [user_group_employee, user_group_project_user, user_group_project_manager, user_group_sales_user,
                     user_group_sales_manager]
        if user_product_customer:
            group_ids.append(user_product_customer)

        # Test user with project access rights for the various tests
        Users = cls.env['res.users'].with_context({'no_reset_password': True})
        cls.user = Users.create({
            'name': 'Project Manager',
            'login': 'misterpm',
            'password': 'misterpm',
            'email': 'mrpm@testco.com',
            'signature': 'Mr. PM',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id, user_group_project_manager.id,
                                  user_group_sales_user.id])]
        })
        hours_uom = cls.env['uom.uom'].search([('name', '=', 'Hour')]) or False
        # Test product to use with the various tests
        cls.task1 = cls.env['project.task.template'].create({
            'name': 'Template 1',
        })
        cls.project = cls.env['project.project'].create({
            'name': 'Test Project',
        })
        cls.product_task_global_project = cls.env['product.product'].create({
            'name': 'Test Product 1',
            'type': 'service',
            'service_tracking': 'task_global_project',
            'project_id': cls.project.id,
            'task_template_id': cls.task1.id,
            'uom_id': hours_uom.id,
            'uom_po_id': hours_uom.id,
        })
        cls.product_task_in_project = cls.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'service',
            'service_tracking': 'task_in_project',
            'task_template_id': cls.task1.id,
            'uom_po_id': hours_uom.id,
            'uom_id': hours_uom.id,
        })

        # Set up a task template tree with 2 children and 1 grandchild
        cls.parent_task = cls.env['project.task.template'].create({
            'name': 'Parent Template',
        })
        cls.child_task_1 = cls.env['project.task.template'].create({
            'name': 'Child Template 1',
            'parent': cls.parent_task.id,
        })
        cls.child_task_2 = cls.env['project.task.template'].create({
            'name': 'Child Template 2',
            'parent': cls.parent_task.id,
        })
        cls.parent_task.write({'subtasks': [Command.set([cls.child_task_1.id, cls.child_task_2.id])]})
        cls.grandchild_task = cls.env['project.task.template'].create({
            'name': 'Grandchild Template',
            'parent': cls.child_task_2.id
        })
        cls.child_task_2.write({'subtasks': [Command.set([cls.grandchild_task.id])]})

        # Create products using the task tree we just created
        cls.product_task_tree_global_project = cls.env['product.product'].create({
            'name': 'Test Product 3',
            'type': 'service',
            'service_tracking': 'task_global_project',
            'project_id': cls.project.id,
            'task_template_id': cls.parent_task.id,
            'uom_id': hours_uom.id,
            'uom_po_id': hours_uom.id,
        })
        cls.product_task_tree_in_project = cls.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'service',
            'service_tracking': 'task_in_project',
            'task_template_id': cls.parent_task.id,
            'uom_po_id': hours_uom.id,
            'uom_id': hours_uom.id,
        })


@tagged('-at_install', 'post_install')
class TestTaskTemplate(TestTaskTemplateCommon):

    def test_delete_task_template(self):
        """User should never be able to delete a task template used on a product"""
        with self.assertRaises(ForeignKeyViolation):
            self.task1.unlink()

    def test_delete_subtask_template(self):
        """ Deletion of a child task should be OK even if the parent is on a product. Children of the deleted
        subtask should be deleted."""
        self.child_task_2.unlink()
        # Reading deleted child's name field should be impossible
        with self.assertRaises(MissingError):
            test = self.grandchild_task.name


@tagged('-at_install', 'post_install')
class TestTaskTemplateTour(HttpCase, TestTaskTemplateCommon):

    def test_task_template_tour(self):
        self.start_tour('/web', 'task_template_tour',
                        login='misterpm', )