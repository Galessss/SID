# SID - Sistema Integrado de Gestão 🚀

O SID (Sistema Integrado) é um ecossistema de gestão empresarial (ERP) desenvolvido para automatizar processos de vendas, controle de estoque e análise de desempenho. Projetado para ser multiúso, o sistema se adapta tanto ao comércio de bens quanto à prestação de serviços que utilizam catálogos de itens.

🛠️ Funcionalidades de Gestão
📈 Inteligência Financeira e Dashboards
Monitoramento Temporal: Visão detalhada do faturamento diário, semanal e mensal.

Controle de Metas: Sistema de barra de progresso em tempo real que compara o desempenho atual com a meta diária configurada pelo gestor.

Evolução de Itens: Gráficos dinâmicos que mostram a tendência de saída dos produtos mais vendidos.

Métricas Vitalícias: Contador de faturamento total, volume de pedidos e engajamento do catálogo público.

📦 Catálogo e Estoque Inteligente
Gestão Ágil: Cadastro completo de itens com precificação, descrição e controle de imagens.

Categorização Dinâmica: Sistema de criação de categorias "on-the-fly" diretamente no formulário de cadastro de produtos.

Status em Tempo Real: Alternância instantânea de disponibilidade (Ativo/Inativo) via API, refletindo imediatamente na visão do cliente.

Manutenção de Dados: Gerenciador de categorias com travas de segurança contra exclusão de itens vinculados.

🌐 Interface Pública (Vitrine Digital)
Visão do Cliente: Interface limpa e otimizada para dispositivos móveis, permitindo que o cliente visualize apenas o que está disponível em tempo real.

Segmentação Automática: O sistema organiza a vitrine automaticamente, exibindo apenas categorias que possuem itens em estoque ou ativos.

⚙️ Configurações de Negócio
Perfil do Estabelecimento: Customização de horários de abertura/fechamento e dias de funcionamento.

Personalização Visual: Suporte a fotos de capa e identidade visual flexível para diferentes tipos de empresas.

💻 Tecnologias Utilizadas
O projeto utiliza uma stack moderna focada em escalabilidade e performance:

Core: Python 3.14+ e Django 6.0.

Banco de Dados: PostgreSQL (Hospedado via Supabase).

Frontend: Bootstrap 5.3 com suporte nativo a Dark/Light Mode.

Gráficos: Chart.js (Integração JSON via Django).

Iconografia: Bootstrap Icons.

🚀 Como Rodar o Projeto
Clone o repositório:

Bash
git clone https://github.com/marcus-balbino/sid-projeto.git
Configure o ambiente:
Crie sua virtualenv e instale os pacotes necessários:

Bash
pip install -r requirements.txt
Sincronize o Banco de Dados:

Bash
python manage.py migrate
Inicie o Sistema:

Bash
python manage.py runserver 8080
👤 Autor
Desenvolvido por Marcus Vinicius Guimarães Balbino como parte de sua trajetória em Ciência da Computação na UFT.
