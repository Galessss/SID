# SID - Sistema Integrado de Delivery 🐧
O SID é uma plataforma completa de gestão de vendas e logística, projetada para conectar lojistas, transportadoras e clientes finais em um ecossistema unificado e em tempo real. Desenvolvido com foco em agilidade operacional, o sistema oferece dashboards dinâmicos, gestão de frota robusta e monitoramento detalhado de entregas.

# 🚀 Principais Módulos
# 1. Painel do Lojista (Dashboard)
Gestão centralizada da operação de venda e produção.

Monitoramento em Tempo Real: Sincronização automática de novos pedidos com alertas sonoros.

Gestão de Status: Fluxo completo desde "Pendente" até "Pronto" ou "Cancelado" via AJAX (sem recarregar a página).

Métricas Financeiras: Gráficos de evolução de vendas (Chart.js), faturamento diário/semanal/mensal e barra de progresso de metas.

Catálogo & Estoque: Controle total de produtos e insumos.

# 2. Central de Despacho (Logística)
Módulo exclusivo para transportadoras gerenciarem a distribuição.

Atribuição Inteligente: O operador da central seleciona qual motoboy realizará cada entrega.

Monitoramento de Frota: Acompanhamento visual de pedidos "Aguardando Atribuição" vs. "Em Rota".

Segurança Operacional: Bloqueio de cancelamento para pedidos já entregues e exclusão de auto-atribuição para operadores.

# 3. Gestão de Equipe & Frota
Ficha cadastral robusta para o gerenciamento de entregadores.

Dados Detalhados: Registro de CPF, CNH, tipo de veículo (Moto, Carro, Bicicleta) e placa.

Controle de Acesso: Operadores podem gerenciar a frota, mas são protegidos contra auto-exclusão.

# 4. Histórico & Auditoria
Transparência total sobre a operação passada.

Busca Geral: Filtro inteligente por ID, Cliente, Bairro, Loja ou Motoboy.

Timeline Detalhada: Registro exato dos horários de criação, despacho e entrega final.

Responsabilidade: Identificação clara de qual operador despachou e qual motoboy entregou cada pedido.

# 🛠️ Tecnologias Utilizadas
Backend: Python 3.14+ / Django 6.0+

Frontend: HTML5, CSS3 (Bootstrap 5), JavaScript (ES6+)

Banco de Dados: SQLite (Desenvolvimento) / PostgreSQL (Sugerido para Produção)

Gráficos: Chart.js

Ícones: Bootstrap Icons

Comunicação: AJAX / Fetch API para atualizações assíncronas

📸 Interface
O sistema conta com um design moderno em Dark Mode automático (baseado no horário ou preferência do usuário), garantindo conforto visual para operadores que trabalham em turnos noturnos.

⚙️ Instalação e Execução
Clonar o repositório:

Bash
git clone https://github.com/seu-usuario/sid.git
Instalar dependências:

Bash
pip install -r requirements.txt
Aplicar migrações:

Bash
python manage.py makemigrations
python manage.py migrate
Iniciar o servidor:

Bash
python manage.py runserver
👤 Autor
Desenvolvido por Marcus Vinicius Guimarães Balbino.
Estudante de Ciência da Computação na Universidade Federal do Tocantins (UFT).

SID - MVB Desenvolvimento V.0.01 Beta
