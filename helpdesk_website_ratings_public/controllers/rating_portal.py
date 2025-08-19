# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from datetime import datetime, timedelta

class HelpdeskWebsiteRatings(http.Controller):

    @http.route(['/helpdesk/rating'], type='http', auth='public', website=True, sitemap=True)
    def helpdesk_ratings(self, **kwargs):
        # Solo equipos con ratings publicados (opcional)
        teams = request.env['helpdesk.team'].sudo().search([])
        team_dicts = []

        # Ventanas de tiempo para métricas rápidas (igual que v17)
        durations = [7, 30, 90]

        Rating = request.env['rating.rating'].sudo()
        for team in teams:
            # ratings consumidos del modelo helpdesk.ticket para el equipo
            ratings = Rating.search([
                ('consumed', '=', True),
                ('res_model', '=', 'helpdesk.ticket'),
                ('parent_ref', '=', 'helpdesk.team,%d' % team.id),
            ], order='create_date desc', limit=100)

            # Stats por ventana (conteo y promedio simple)
            stats = {}
            for d in durations:
                since = fields.Datetime.to_string(datetime.utcnow() - timedelta(days=d))
                rs = Rating.search([
                    ('consumed', '=', True),
                    ('res_model', '=', 'helpdesk.ticket'),
                    ('parent_ref', '=', 'helpdesk.team,%d' % team.id),
                    ('create_date', '>', since),
                ])
                if rs:
                    avg = sum(r.rating for r in rs if r.rating) / len(rs)
                else:
                    avg = 0.0
                stats[d] = {
                    'count': len(rs),
                    'avg': round(avg, 2) if avg else 0.0,
                }

            team_dicts.append({
                'team': team,
                'ratings': ratings,
                'stats': stats,
            })

        values = {
            'teams': team_dicts,
        }
        return request.render('helpdesk_website_ratings_public.team_rating_page', values)
