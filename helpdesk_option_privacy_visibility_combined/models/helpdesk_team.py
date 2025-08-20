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
             "A user with the helpdesk > administrator access right level can still access this team and its tickets, even if they are not explicitly part of the followers.\n\n"
             "- All internal users: all internal users can access the team and all of its tickets without distinction.\n\n"
             "- Invited portal users and all internal users: all internal users can access the team and all of its tickets without distinction.\n"
             "Portal users can only access the tickets they are following. "
             "This access can be modified on each ticket individually by adding or removing the portal user as follower."
    )

    # --- FIX 1: constraint corregida (antes usaba 'or' y siempre disparaba el error) ---
    @api.constrains('use_website_helpdesk_form', 'privacy_visibility')
    def _check_website_privacy(self):
        for team in self:
            if team.use_website_helpdesk_form and team.privacy_visibility not in ('portal', 'combined'):
                raise ValidationError(_(
                    'La visibilidad del equipo debe configurarse en "Usuarios del portal invitado y todos los usuarios internos" '
                    'o "Acceso interno y del portal combinado" para poder utilizar el formulario del sitio web.'
                ))

    # --- FIX 2: warnings calculados con lógica correcta usando 'in/not in' ---
    @api.depends('privacy_visibility')
    def _compute_privacy_visibility_warning(self):
        for team in self:
            if not team.ids:
                team.privacy_visibility_warning = ''
                continue

            new_is_portal_like = team.privacy_visibility in ('portal', 'combined')
            old_is_portal_like = team._origin.privacy_visibility in ('portal', 'combined')

            if new_is_portal_like and not old_is_portal_like:
                team.privacy_visibility_warning = _('Customers will be added to the followers of their tickets.')
            elif (not new_is_portal_like) and old_is_portal_like:
                team.privacy_visibility_warning = _(
                    'Portal users will be removed from the followers of the team and its tickets.'
                )
            else:
                team.privacy_visibility_warning = ''

    def _compute_access_instruction_message(self):
        for team in self:
            if team.privacy_visibility == 'portal':
                team.access_instruction_message = _(
                    'Grant portal users access to your helpdesk team or tickets by adding them as followers. '
                    'Customers automatically get access to their tickets in their portal.'
                )
            elif team.privacy_visibility == 'invited_internal':
                team.access_instruction_message = _(
                    'Grant employees access to your helpdesk team or tickets by adding them as followers. '
                    'Employees automatically get access to the tickets they are assigned to.'
                )
            elif team.privacy_visibility == 'combined':
                team.access_instruction_message = _(
                    'Grant portal users access to your helpdesk team or tickets by adding them as followers. '
                    'Customers automatically get access to their tickets in their portal.\n\n'
                    'Grant employees access to your helpdesk team or tickets by adding them as followers. '
                    'Employees automatically get access to the tickets they are assigned to.'
                )
            else:
                team.access_instruction_message = ''

    def _change_privacy_visibility(self, new_visibility):
        """
        Unsubscribe non-internal users from the team and tickets if the team privacy visibility
        goes from 'portal'/'combined' to a different value.
        If the privacy visibility is set to 'portal' or 'combined', subscribe back tickets partners.
        """
        for team in self:
            if team.privacy_visibility == new_visibility:
                continue

            if new_visibility in ('portal', 'combined'):
                # suscribir clientes a sus tickets si pasamos a un modo con portal
                if new_visibility == 'portal' and team.privacy_visibility != 'combined':
                    for ticket in team.mapped('ticket_ids').filtered('partner_id'):
                        ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
                elif new_visibility == 'combined':
                    if team.privacy_visibility != 'portal':
                        for ticket in team.mapped('ticket_ids').filtered('partner_id'):
                            ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
                    self._update_helpdesk_ticket_user_rule_domain('to_combined')

            elif team.privacy_visibility in ('portal', 'combined') and new_visibility not in ('portal', 'combined'):
                # nos vamos de un modo con portal -> quitar seguidores portal y reajustar reglas
                portal_users = team.message_partner_ids.user_ids.filtered('share')
                team.message_unsubscribe(partner_ids=portal_users.partner_id.ids)
                team.mapped('ticket_ids')._unsubscribe_portal_users()
                self._update_helpdesk_ticket_user_rule_domain('to_internal')

    def _update_helpdesk_ticket_user_rule_domain(self, state):
        IrRule = self.env['ir.rule']

        if state == 'to_combined':
            # Ajustar reglas para usuarios internos
            rule_helpdesk_user_rule = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_user_rule').id)], limit=1)
            if rule_helpdesk_user_rule:
                new_domain = "['&', ('privacy_visibility', '=', 'combined'), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_user_rule.write({'domain_force': new_domain})

            rule_helpdesk_ticket_user_rule = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_user_rule').id)], limit=1)
            if rule_helpdesk_ticket_user_rule:
                new_domain = "['&', ('team_id.privacy_visibility', '=', 'combined'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_ticket_user_rule.write({'domain_force': new_domain})

            # FIX 3: referenciar la regla correcta de SLA (antes apuntaba al model xml_id)
            rule_sla_report_user = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_sla_report_analysis_rule_user').id)], limit=1)
            if rule_sla_report_user:
                new_domain = "['&', ('team_id.privacy_visibility', '=', 'combined'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('ticket_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_sla_report_user.write({'domain_force': new_domain})

            rule_ticket_report_user = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_report_analysis_rule_user').id)], limit=1)
            if rule_ticket_report_user:
                new_domain = "['&', ('team_id.privacy_visibility', '=', 'combined'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('ticket_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_ticket_report_user.write({'domain_force': new_domain})

            # Ajustar regla para portal
            rule_helpdesk_portal_ticket_rule = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_portal_ticket_rule').id)], limit=1)
            if rule_helpdesk_portal_ticket_rule:
                new_domain = "['&', ('team_privacy_visibility', '=', 'combined'), '|', ('message_partner_ids', 'in', [user.partner_id.id]), ('team_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_portal_ticket_rule.write({'domain_force': new_domain})

        elif state == 'to_internal':
            # Reajustar reglas a su dominio "clásico" (sin combined)
            rule_helpdesk_user_rule = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_user_rule').id)], limit=1)
            if rule_helpdesk_user_rule:
                old_domain = "['|', ('privacy_visibility', '!=', 'invited_internal'), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_user_rule.write({'domain_force': old_domain})

            rule_helpdesk_ticket_user_rule = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_user_rule').id)], limit=1)
            if rule_helpdesk_ticket_user_rule:
                old_domain = "['|', '|', ('team_id.privacy_visibility', '!=', 'invited_internal'), ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_ticket_user_rule.write({'domain_force': old_domain})

            rule_sla_report_user = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_sla_report_analysis_rule_user').id)], limit=1)
            if rule_sla_report_user:
                old_domain = "['|', ('team_id.privacy_visibility', '!=', 'invited_internal'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_sla_report_user.write({'domain_force': old_domain})

            rule_ticket_report_user = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_ticket_report_analysis_rule_user').id)], limit=1)
            if rule_ticket_report_user:
                old_domain = "['|', ('team_id.privacy_visibility', '!=', 'invited_internal'), '|', ('team_id.message_partner_ids', 'in', [user.partner_id.id]), ('message_partner_ids', 'in', [user.partner_id.id])]"
                rule_ticket_report_user.write({'domain_force': old_domain})

            # Reajustar regla portal
            rule_helpdesk_portal_ticket_rule = IrRule.search([('id', '=', self.env.ref('helpdesk.helpdesk_portal_ticket_rule').id)], limit=1)
            if rule_helpdesk_portal_ticket_rule:
                old_domain = "['&', ('team_privacy_visibility', '=', 'portal'), '|', ('message_partner_ids', 'in', [user.partner_id.id]), ('team_id.message_partner_ids', 'in', [user.partner_id.id])]"
                rule_helpdesk_portal_ticket_rule.write({'domain_force': old_domain})
