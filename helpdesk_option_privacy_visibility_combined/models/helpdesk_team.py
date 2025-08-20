from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    privacy_visibility = fields.Selection([
        ('invited_internal', 'Invited internal users (private)'),
        ('internal', 'All internal users (company)'),
        ('portal', 'Invited portal users and all internal users (public)'),
        ('combined', 'Combined Internal and Portal Access'),  # Nueva opción añadida
    ],
        string='Visibility', required=True,
        default='portal',
        help="People to whom this helpdesk team and its tickets will be visible.\n\n"
             "- Invited internal users: internal users can access the team and the tickets they are following. "
             "This access can be modified on each ticket individually by adding or removing the user as follower.\n"
             "A user with the helpdesk > administrator access right level can still access this team and its tickets, even if they are not explicitely part of the followers.\n\n"
             "- All internal users: all internal users can access the team and all of its tickets without distinction.\n\n"
             "- Invited portal users and all internal users: all internal users can access the team and all of its tickets without distinction.\n"
             "Portal users can only access the tickets they are following. "
             "This access can be modified on each ticket individually by adding or removing the portal user as follower.")

    @api.constrains('use_website_helpdesk_form', 'privacy_visibility')
    def _check_website_privacy(self):
        if any(t.use_website_helpdesk_form and (t.privacy_visibility != 'portal' or t.privacy_visibility != 'combined')
               for t in self):
            raise ValidationError(
                _('Team visibility must be set to "Guest portal users and all internal users" or "Combined internal and portal access" in order to use the website form'))

    @api.depends('privacy_visibility')
    def _compute_privacy_visibility_warning(self):
        for team in self:
            if not team.ids:
                team.privacy_visibility_warning = ''
            elif (team.privacy_visibility == 'portal' or team.privacy_visibility == 'combined') and (
                    team._origin.privacy_visibility != 'portal' or team._origin.privacy_visibility != 'combined'):
                team.privacy_visibility_warning = _('Customers will be added to the followers of their tickets.')
            elif (team.privacy_visibility != 'portal' or team.privacy_visibility != 'combined') and (
                    team._origin.privacy_visibility == 'portal' or team._origin.privacy_visibility == 'combined'):
                team.privacy_visibility_warning = _(
                    'Portal users will be removed from the followers of the team and its tickets.')
            else:
                team.privacy_visibility_warning = ''

    @api.depends('privacy_visibility')
    def _compute_access_instruction_message(self):
        for team in self:
            if team.privacy_visibility == 'portal':
                team.access_instruction_message = _(
                    'Grant portal users access to your helpdesk team or tickets by adding them as followers. Customers automatically get access to their tickets in their portal.')
            elif team.privacy_visibility == 'invited_internal':
                team.access_instruction_message = _(
                    'Grant employees access to your helpdesk team or tickets by adding them as followers. Employees automatically get access to the tickets they are assigned to.')
            elif team.privacy_visibility == 'combined':
                team.access_instruction_message = _(
                    'Grant portal users access to your helpdesk team or tickets by adding them as followers. Customers automatically get access to their tickets in their portal.\n\n'
                    'Grant employees access to your helpdesk team or tickets by adding them as followers. Employees automatically get access to the tickets they are assigned to.'
                )
            else:
                team.access_instruction_message = ''

    def _change_privacy_visibility(self, new_visibility):
        """
        Unsubscribe non-internal users from the team and tickets if the team privacy visibility
        goes from 'portal' to a different value.
        If the privacy visibility is set to 'portal', subscribe back tickets partners.
        """
        for team in self:
            if team.privacy_visibility == new_visibility:
                continue
            if new_visibility == 'portal' or new_visibility == 'combined':

                if new_visibility == 'portal' and team.privacy_visibility != 'combined':
                    for ticket in team.mapped('ticket_ids').filtered('partner_id'):
                        ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
                elif new_visibility == 'combined':
                    if team.privacy_visibility != 'portal':
                        for ticket in team.mapped('ticket_ids').filtered('partner_id'):
                            ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
                    self._update_helpdesk_ticket_user_rule_domain('to_combined')

            elif team.privacy_visibility == 'portal' and new_visibility != 'combined':
                portal_users = team.message_partner_ids.user_ids.filtered('share')
                team.message_unsubscribe(partner_ids=portal_users.partner_id.ids)
                team.mapped('ticket_ids')._unsubscribe_portal_users()
                self._update_helpdesk_ticket_user_rule_domain('to_internal')
            elif team.privacy_visibility == 'combined' and new_visibility != 'portal':
                portal_users = team.message_partner_ids.user_ids.filtered('share')
                team.message_unsubscribe(partner_ids=portal_users.partner_id.ids)
                team.mapped('ticket_ids')._unsubscribe_portal_users()
                self._update_helpdesk_ticket_user_rule_domain('to_internal')

    @api.model
    def _update_helpdesk_ticket_user_rule_domain(self, state):
        if state == 'to_combined':
            #Ajustar regla para INTERNAL
            # Buscar la regla de acceso por su ID
            rule_helpdesk_user_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_user_rule').id)], limit=1)
            if rule_helpdesk_user_rule:
                # Aquí defines el nuevo dominio que deseas establecer
                new_domain = "['&', ('privacy_visibility', '=', 'combined'), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_user_rule.write({'domain_force': new_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Buscar la regla de acceso por su ID
            rule_helpdesk_ticket_user_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_user_rule').id)], limit=1)
            if rule_helpdesk_ticket_user_rule:
                # Aquí defines el nuevo dominio que deseas establecer
                new_domain = "['&', ('team_id.privacy_visibility', '=', 'combined'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_ticket_user_rule.write({'domain_force': new_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Buscar la regla de acceso por su ID
            rule_helpdesk_sla_report_analysis_rule_user = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.model_helpdesk_sla_report_analysis').id)], limit=1)
            if rule_helpdesk_sla_report_analysis_rule_user:
                # Aquí defines el nuevo dominio que deseas establecer
                new_domain = "['&', ('team_id.privacy_visibility', '=', 'combined'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('ticket_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_sla_report_analysis_rule_user.write({'domain_force': new_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Buscar la regla de acceso por su ID
            rule_helpdesk_ticket_user_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_report_analysis_rule_user').id)], limit=1)
            if rule_helpdesk_ticket_user_rule:
                # Aquí defines el nuevo dominio que deseas establecer
                new_domain = "['&', ('team_id.privacy_visibility', '=', 'combined'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('ticket_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_ticket_user_rule.write({'domain_force': new_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            #Ajustar regla para PORTAL
            # Buscar la regla de acceso por su ID
            rule_helpdesk_portal_ticket_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_portal_ticket_rule').id)], limit=1)
            if rule_helpdesk_portal_ticket_rule:
                # Aquí defines el nuevo dominio que deseas establecer
                new_domain = "['&', ('team_privacy_visibility', '=', 'combined'), '|', ('message_partner_ids', 'in', [user.partner_id.id]), ('team_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_portal_ticket_rule.write({'domain_force': new_domain})
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            #Reajustar regla de INTERNAL
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        elif state == 'to_internal':
            # Buscar la regla de acceso por su ID
            rule_helpdesk_user_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_user_rule').id)], limit=1)
            if rule_helpdesk_user_rule:
                # Aquí defines el viejo dominio que deseas establecer
                old_domain = "['|', ('privacy_visibility', '!=', 'invited_internal'), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_user_rule.write({'domain_force': old_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Buscar la regla de acceso por su ID
            rule_helpdesk_ticket_user_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_user_rule').id)], limit=1)
            if rule_helpdesk_ticket_user_rule:
                # Aquí defines el viejo dominio que deseas establecer
                old_domain = "['|', '|', ('team_id.privacy_visibility', '!=', 'invited_internal'), ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_ticket_user_rule.write({'domain_force': old_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Buscar la regla de acceso por su ID
            rule_helpdesk_sla_report_analysis_rule_user = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_sla_report_analysis_rule_user').id)], limit=1)
            if rule_helpdesk_sla_report_analysis_rule_user:
                # Aquí defines el viejo dominio que deseas establecer
                old_domain = "['|',('team_id.privacy_visibility', '!=', 'invited_internal'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_sla_report_analysis_rule_user.write({'domain_force': old_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            # Buscar la regla de acceso por su ID
            rule_helpdesk_ticket_report_analysis_rule_user = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_report_analysis_rule_user').id)], limit=1)
            if rule_helpdesk_ticket_report_analysis_rule_user:
                # Aquí defines el viejo dominio que deseas establecer
                old_domain = "['|',('team_id.privacy_visibility', '!=', 'invited_internal'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_ticket_report_analysis_rule_user.write({'domain_force': old_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

            #Reajustar regla de PORTAL
            # Buscar la regla de acceso por su ID
            rule_helpdesk_portal_ticket_rule = self.env['ir.rule'].search([('id', '=', self.env.ref('helpdesk.helpdesk_portal_ticket_rule').id)], limit=1)
            if rule_helpdesk_portal_ticket_rule:
                # Aquí defines el viejo dominio que deseas establecer
                old_domain = "['&', ('team_privacy_visibility', '=', 'portal'), '|', ('message_partner_ids', 'in', [user.partner_id.id]), ('team_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_portal_ticket_rule.write({'domain_force': old_domain})
            # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
