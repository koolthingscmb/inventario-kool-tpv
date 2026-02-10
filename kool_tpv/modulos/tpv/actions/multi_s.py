"""Controlador para cobro mixto (Efectivo + Tarjeta).

Provee una pequeña UI en la zona de `carrito_ui._cash_container` que permite
introducir un importe en efectivo y otro en tarjeta. Mantiene la suma
sincronizada con el total y delega la persistencia a `on_finalize`.
"""

import logging
import tkinter as tk
from decimal import Decimal, InvalidOperation


class MultiPagoController:
	def __init__(self, carrito_ui, carrito_service, on_finalize=None):
		self.carrito_ui = carrito_ui
		self.carrito_service = carrito_service
		self.on_finalize = on_finalize
		self._updating = False
		self.state = 'inactive'

		# UI refs
		self._container = None
		self._entry_ef = None
		self._entry_tar = None
		self.var_efectivo = None
		self.var_tarjeta = None
		self._lbl_info = None

		# register controller in CarritoUI for exclusivity management
		try:
			if hasattr(self.carrito_ui, 'register_controller') and callable(getattr(self.carrito_ui, 'register_controller')):
				try:
					self.carrito_ui.register_controller(self)
				except Exception:
					pass
		except Exception:
			pass

	def deactivate(self):
		"""Destruye widgets creados en _cash_container y resetea el estado."""
		try:
			# destroy only our main frame (other widgets are shared)
			try:
				if getattr(self, '_main_frame', None):
					try:
						self._main_frame.destroy()
					except Exception:
						pass
			except Exception:
				logging.exception('Error destruyendo main_frame en deactivate MultiPagoController')

			try:
				self.carrito_ui.set_cash_active(False)
			except Exception:
				pass

			# reset state and refs
			self._updating = False
			self.state = 'inactive'
			self._container = None
			self._entry_ef = None
			self._entry_tar = None
			self.var_efectivo = None
			self.var_tarjeta = None
			self._lbl_info = None
		except Exception:
			logging.exception('Error en deactivate MultiPagoController')

	def _activate(self):
		try:
			# guard: do not activate if cart is empty
			try:
				empty = False
				if getattr(self.carrito_service, 'is_empty', None) and callable(self.carrito_service.is_empty):
					empty = self.carrito_service.is_empty()
				else:
					empty = (self.carrito_service.get_item_count() == 0)
				if empty:
					try:
						if hasattr(self.carrito_ui, 'show_temporary_message') and callable(getattr(self.carrito_ui, 'show_temporary_message')):
							self.carrito_ui.show_temporary_message('NO HAY ARTÍCULOS', duration_ms=2500)
						else:
							logging.info('NO HAY ARTÍCULOS')
					except Exception:
						logging.exception('Error mostrando mensaje carrito vacío desde MultiPagoController')
					return
			except Exception:
				logging.exception('Error comprobando carrito vacío en MultiPagoController')

			# ensure exclusivity
			try:
				if hasattr(self.carrito_ui, 'deactivate_all_controllers') and callable(getattr(self.carrito_ui, 'deactivate_all_controllers')):
					try:
						self.carrito_ui.deactivate_all_controllers(except_controller=self)
					except Exception:
						pass
			except Exception:
				pass

			total = Decimal('0')
			try:
				total = Decimal(str(self.carrito_service.get_total()))
			except Exception:
				try:
					resumen = getattr(self.carrito_service, 'get_resumen_financiero') and self.carrito_service.get_resumen_financiero()
					total = Decimal(str(resumen.get('total', '0'))) if resumen else Decimal('0')
				except Exception:
					total = Decimal('0')

			container = getattr(self.carrito_ui, '_cash_container', None)
			if container is None:
				return
			self._container = container

			# hide existing widgets in container (do not destroy shared widgets)
			try:
				for w in list(container.winfo_children()):
					try:
						w.grid_remove()
					except Exception:
						pass
			except Exception:
				pass

			# visual style
			try:
				container.config(bg='#2f4f4f')
			except Exception:
				pass

			# Variables
			self.var_efectivo = tk.StringVar(value='0.00')
			self.var_tarjeta = tk.StringVar(value=f"{total:.2f}")

			# Create a dedicated frame for our widgets so we can remove it without
			# affecting shared widgets created by other controllers.
			try:
				self._main_frame = tk.Frame(container, bg=container.cget('bg'))
				# Layout inside main_frame
				lbl_e = tk.Label(self._main_frame, text='EFECTIVO', fg='#FFFFFF', bg=self._main_frame.cget('bg'), font=('Roboto-Bold', 14))
				lbl_e.grid(row=0, column=0, sticky='w', padx=4, pady=4)
				self._entry_ef = tk.Entry(self._main_frame, textvariable=self.var_efectivo, font=('Roboto', 14))
				self._entry_ef.grid(row=0, column=1, sticky='we', padx=4, pady=4)

				lbl_t = tk.Label(self._main_frame, text='TARJETA', fg='#FFFFFF', bg=self._main_frame.cget('bg'), font=('Roboto-Bold', 14))
				lbl_t.grid(row=1, column=0, sticky='w', padx=4, pady=4)
				self._entry_tar = tk.Entry(self._main_frame, textvariable=self.var_tarjeta, font=('Roboto', 14))
				self._entry_tar.grid(row=1, column=1, sticky='we', padx=4, pady=4)

				# info label and help
				self._lbl_info = tk.Label(self._main_frame, text='Enter para confirmar', fg='#FFFFFF', bg=self._main_frame.cget('bg'), font=('Roboto', 12))
				self._lbl_info.grid(row=2, column=0, columnspan=2, sticky='we', padx=4, pady=(8, 2))

				self._main_frame.grid(row=0, column=0, columnspan=2, sticky='we')
				container.columnconfigure(1, weight=1)
			except Exception:
				logging.exception('Error creando widgets MultiPagoController')

			# Bindings
			try:
				# trace callbacks
				try:
					self.var_efectivo.trace_add('write', lambda *args: self._on_efectivo_change())
				except Exception:
					try:
						self.var_efectivo.trace('w', lambda *args: self._on_efectivo_change())
					except Exception:
						pass
				try:
					self.var_tarjeta.trace_add('write', lambda *args: self._on_tarjeta_change())
				except Exception:
					try:
						self.var_tarjeta.trace('w', lambda *args: self._on_tarjeta_change())
					except Exception:
						pass

				# Enter bindings
				try:
					self._entry_ef.bind('<Return>', lambda e: self._confirm())
				except Exception:
					pass
				try:
					self._entry_tar.bind('<Return>', lambda e: self._confirm())
				except Exception:
					pass
			except Exception:
				logging.exception('Error enlazando eventos MultiPagoController')

			try:
				self.carrito_ui.set_cash_active(True)
			except Exception:
				pass

			self.state = 'active'
		except Exception:
			logging.exception('Error en _activate MultiPagoController')

	def _parse_decimal(self, txt: str) -> Decimal:
		try:
			if txt is None:
				return Decimal('0')
			return Decimal(str(txt).strip())
		except (InvalidOperation, ValueError):
			return Decimal('0')

	def _on_efectivo_change(self):
		try:
			if self._updating:
				return
			self._updating = True
			try:
				total = Decimal('0')
				try:
					total = Decimal(str(self.carrito_service.get_total()))
				except Exception:
					try:
						resumen = getattr(self.carrito_service, 'get_resumen_financiero') and self.carrito_service.get_resumen_financiero()
						total = Decimal(str(resumen.get('total', '0'))) if resumen else Decimal('0')
					except Exception:
						total = Decimal('0')

				val_ef = self._parse_decimal(self.var_efectivo.get())
				nuevo_tar = total - val_ef
				info = ''
				if nuevo_tar <= 0:
					# overpaid in efectivo: tarjeta 0 and show change
					nuevo_tar = Decimal('0')
					cambio = val_ef - total
					info = f'Cambio: {cambio:.2f} €'
				# update tarjeta var without triggering reciprocal update
				try:
					self.var_tarjeta.set(f"{nuevo_tar:.2f}")
				except Exception:
					pass
				try:
					if self._lbl_info is not None and info:
						self._lbl_info.config(text=info)
					else:
						try:
							self._lbl_info.config(text='Enter para confirmar')
						except Exception:
							pass
				except Exception:
					pass
			finally:
				self._updating = False
		except Exception:
			logging.exception('Error en _on_efectivo_change MultiPagoController')

	def _on_tarjeta_change(self):
		try:
			if self._updating:
				return
			self._updating = True
			try:
				total = Decimal('0')
				try:
					total = Decimal(str(self.carrito_service.get_total()))
				except Exception:
					try:
						resumen = getattr(self.carrito_service, 'get_resumen_financiero') and self.carrito_service.get_resumen_financiero()
						total = Decimal(str(resumen.get('total', '0'))) if resumen else Decimal('0')
					except Exception:
						total = Decimal('0')

				val_tar = self._parse_decimal(self.var_tarjeta.get())
				nuevo_ef = total - val_tar
				info = ''
				if nuevo_ef <= 0:
					nuevo_ef = Decimal('0')
					cambio = val_tar - total
					info = f'Cambio: {cambio:.2f} €'
				try:
					self.var_efectivo.set(f"{nuevo_ef:.2f}")
				except Exception:
					pass
				try:
					if self._lbl_info is not None and info:
						self._lbl_info.config(text=info)
					else:
						try:
							self._lbl_info.config(text='Enter para confirmar')
						except Exception:
							pass
				except Exception:
					pass
			finally:
				self._updating = False
		except Exception:
			logging.exception('Error en _on_tarjeta_change MultiPagoController')

	def _confirm(self, event=None):
		try:
			# parse values
			val_ef = self._parse_decimal(self.var_efectivo.get()) if self.var_efectivo is not None else Decimal('0')
			val_tar = self._parse_decimal(self.var_tarjeta.get()) if self.var_tarjeta is not None else Decimal('0')
			try:
				total = Decimal(str(self.carrito_service.get_total()))
			except Exception:
				try:
					resumen = getattr(self.carrito_service, 'get_resumen_financiero') and self.carrito_service.get_resumen_financiero()
					total = Decimal(str(resumen.get('total', '0'))) if resumen else Decimal('0')
				except Exception:
					total = Decimal('0')

			suma = val_ef + val_tar
			if suma < total:
				try:
					if self._lbl_info is not None:
						self._lbl_info.config(text='Importe insuficiente')
				except Exception:
					pass
				return

			# call finalize: pass efectivo as sum and breakdown
			try:
				if callable(self.on_finalize):
					try:
						self.on_finalize(suma, forma_pago='Mixto', importe_efectivo=val_ef, importe_tarjeta=val_tar)
					except TypeError:
						# fallback to older signature
						try:
							self.on_finalize(suma)
						except Exception:
							logging.exception('Error calling on_finalize from MultiPagoController')
				else:
					try:
						self.carrito_service.clear()
						self.carrito_ui.update_display()
					except Exception:
						logging.exception('Error clearing carrito after mixed payment finalize')
			finally:
				try:
					self.deactivate()
				except Exception:
					pass
		except Exception:
			logging.exception('Error en _confirm MultiPagoController')

	def _on_action(self):
		try:
			if self.state == 'inactive':
				self._activate()
				return
			# if active, deactivate
			if self.state == 'active':
				try:
					self.deactivate()
				except Exception:
					logging.exception('Error desactivando MultiPagoController')
				return
		except Exception:
			logging.exception('Error en _on_action MultiPagoController')

