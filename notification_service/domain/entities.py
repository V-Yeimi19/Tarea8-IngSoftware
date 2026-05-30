from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass
class NotificationRequest:
    recipient_email: str
    card_number: str
    points_earned: int
    cashback_amount: Decimal
    total_points_balance: int
    total_cashback_balance: Decimal
    restaurant_code: str
    transaction_id: str
    processed_at: datetime

    def to_email_subject(self) -> str:
        return f"¡Recompensa acreditada! +{self.points_earned} puntos en {self.restaurant_code}"

    def to_email_body_html(self) -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #2c7a2c; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">¡Tu recompensa fue procesada!</h1>
            </div>
            <div style="padding: 30px; background-color: #f9f9f9;">
                <p>Estimado cliente con tarjeta <strong>{self.card_number}</strong>,</p>
                <p>Tu consumo en el restaurante <strong>{self.restaurant_code}</strong> fue registrado exitosamente.</p>

                <div style="background-color: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #2c7a2c;">
                    <h2 style="color: #2c7a2c;">Recompensas de esta transacción</h2>
                    <table width="100%" cellpadding="8">
                        <tr>
                            <td><strong>Puntos ganados:</strong></td>
                            <td style="text-align: right; color: #2c7a2c; font-size: 1.2em;"><strong>+{self.points_earned} pts</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Cashback acreditado:</strong></td>
                            <td style="text-align: right; color: #2c7a2c; font-size: 1.2em;"><strong>S/ {self.cashback_amount:.2f}</strong></td>
                        </tr>
                    </table>
                </div>

                <div style="background-color: white; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h2>Tu balance acumulado</h2>
                    <table width="100%" cellpadding="8">
                        <tr>
                            <td>Total de puntos:</td>
                            <td style="text-align: right;"><strong>{self.total_points_balance} pts</strong></td>
                        </tr>
                        <tr>
                            <td>Total cashback:</td>
                            <td style="text-align: right;"><strong>S/ {self.total_cashback_balance:.2f}</strong></td>
                        </tr>
                    </table>
                </div>

                <p style="color: #666; font-size: 0.85em;">
                    ID de transacción: {self.transaction_id}<br>
                    Procesado: {self.processed_at.strftime('%d/%m/%Y %H:%M:%S UTC')}
                </p>
            </div>
            <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 0.8em;">
                <p>Programa de Recompensas Restaurantes © 2026</p>
            </div>
        </body>
        </html>
        """
