from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Pedido

class Command(BaseCommand):
    help = 'Remove pedidos (carrinhos) não finalizados com mais de 24 horas'

    def handle(self, *args, **kwargs):
        # 1. Define o limite de tempo (24 horas atrás)
        limite_tempo = timezone.now() - timedelta(hours=24)
        
        # 2. Busca os pedidos que são apenas carrinhos abandonados
        carrinhos_abandonados = Pedido.objects.filter(
            finalizado=False,
            data_criacao__lt=limite_tempo
        )
        
        # 3. Conta quantos existem antes de apagar (para o relatório)
        quantidade = carrinhos_abandonados.count()
        
        if quantidade > 0:
            # 4. Deleta em massa de forma eficiente
            carrinhos_abandonados.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Sucesso! {quantidade} carrinhos fantasmas foram apagados do banco de dados.')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Nenhum carrinho abandonado encontrado. O banco já está limpo!')
            )