# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    production_date = fields.Datetime(string="Production Date")

  
class StockMoveline(models.Model):
	_inherit = 'stock.move.line'

	production_date = fields.Datetime(string="Production Date")
	product_package_id = fields.Many2one("product.packaging",string="Package")
	qty_to_mul = fields.Integer('Qty of Package')

	@api.onchange('product_package_id', 'qty_to_mul')
	def _onchange_product_package_id(self):
		if self.product_package_id and self.qty_to_mul > 0:
			self.qty_done = self.product_package_id.qty * self.qty_to_mul

	@api.onchange('product_id', 'product_uom_id', 'lot_id')
	def _onchange_product_id(self):
		res = super(StockMoveline, self)._onchange_product_id()
		if self.lot_id.production_date:
			self.production_date = self.lot_id.production_date

		if self.picking_type_use_create_lots:
			if self.product_id.use_expiration_date:
				self.expiration_date = (self.production_date or fields.Datetime.today(
				)) + datetime.timedelta(days=self.product_id.expiration_time)

			else:
				self.expiration_date = False
		return res

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in res.filtered(lambda mv: mv.picking_type_id.code == 'incoming'):
            for mv_line in move.move_line_ids:
                if mv_line.product_id and mv_line.product_id.use_expiration_date:
                    lot_id = mv_line.lot_id
                    if mv_line.lot_id and mv_line.production_date:
                        mapped_fields = {
                            'expiration_date': 'expiration_time',
                            'use_date': 'use_time',
                            'removal_date': 'removal_time',
                            'alert_date': 'alert_time'
                        }
                        lot_vals = dict.fromkeys(mapped_fields, False)
                        product = self.env['product.product'].browse(
                            mv_line.product_id.id)
                        if product:
                            for field in mapped_fields:
                                duration = getattr(product, mapped_fields[field])
                                if duration:
                                    date = mv_line.production_date + \
                                        datetime.timedelta(days=duration)
                                    lot_vals[field] = fields.Datetime.to_string(
                                        date)
                                lot_vals.update({
                                    'production_date': mv_line.production_date
                                })
                                
                                lot_id.write(lot_vals)
        return res
