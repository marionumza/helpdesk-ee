# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import http, fields
from odoo.http import request

class HelpdeskWebsiteRatings(http.Controller):

    @http.route([
        '/helpdesk/rating_public',
        '/helpdesk/rating_public/',
        '/helpdesk/rating_customer',
        '/helpdesk/rating_customer/',
    ], type='http', auth='public', website=True, sitemap=True)
    def helpdesk_ratings_public(self, **kwargs):
        teams = request.env['helpdesk.team'].sudo().search([])
        durations = [7, 30, 90]
        Rating = request.env['rating.rating'].sudo()

        team_dicts = []
        for team in teams:
            # Últimas 100 valoraciones del equipo
            ratings = Rating.search([
                ('consumed', '=', True),
                ('res_model', '=', 'helpdesk.ticket'),
                ('parent_ref', '=', f'helpdesk.team,{team.id}'),
            ], order='create_date desc', limit=100)

            # Métricas por ventana de tiempo
            stats = {}
            for d in durations:
                since = fields.Datetime.to_string(datetime.utcnow() - timedelta(days=d))
                rs = Rating.search([
                    ('consumed', '=', True),
                    ('res_model', '=', 'helpdesk.ticket'),
                    ('parent_ref', '=', f'helpdesk.team,{team.id}'),
                    ('create_date', '>', since),
                ])
                count = len(rs)
                avg = round(sum((r.rating or 0) for r in rs) / count, 2) if count else 0.0
                stats[d] = {"count": count, "avg": avg}

            team_dicts.append({
                "team": team,
                "ratings": ratings,
                "stats": stats,
            })

        values = {"teams": team_dicts}
        return request.render('helpdesk_website_ratings_public.team_rating_page', values)

