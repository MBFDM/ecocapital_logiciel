import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
from auth import check_authentication
from database import BankDatabase
from mysql_config import MySQLDatabase
from receipt_generator import generate_receipt_pdf
from faker import Faker
import time
import base64
import os
from datetime import datetime

check_authentication()

# Configuration de la page
st.set_page_config(
    page_title="Bank Management Dashboard",
    page_icon=":bank:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de la base de données
db = MySQLDatabase()
fake = Faker()

# Style CSS personnalisé
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("assets/styles.css")

# Fonction pour générer un IBAN fictif plus robuste
def generate_iban(country_code="FR"):
    # Génération selon le format IBAN français
    bank_code = f"{fake.random_number(digits=5, fix_len=True):05d}"
    branch_code = f"{fake.random_number(digits=5, fix_len=True):05d}"
    account_number = f"{fake.random_number(digits=11, fix_len=True):011d}"
    national_check = f"{fake.random_number(digits=2, fix_len=True):02d}"
    
    # Calcul des chiffres de contrôle IBAN
    bban = bank_code + branch_code + account_number + national_check + "00"
    bban_digits = int(bban)
    check_digits = 98 - (bban_digits % 97)
    
    return f"{country_code}{check_digits:02d} {bank_code} {branch_code} {account_number} {national_check}"

# Fonction pour générer un numéro de compte unique
def generate_account_number():
    return f"C{fake.random_number(digits=10, fix_len=True):010d}"

# Barre latérale avec le menu
with st.sidebar:
    st.image("assets/logo.png", width=150)
    st.title("Bank Management")

    if st.session_state['authenticated']:
        st.write(f"Connecté en tant que: {st.session_state['user']['username']}")
        if st.button("Déconnexion"):
            st.session_state['authenticated'] = False
            st.rerun()
    
    selected = option_menu(
        menu_title="Menu Principal",
        options=["Tableau de Bord", "Gestion Clients", "Gestion IBAN", "Transactions", "Générer Reçu"],
        icons=["speedometer", "people", "credit-card", "arrow-left-right", "receipt"],
        default_index=0,
    )

# Page Tableau de Bord
if selected == "Tableau de Bord":
    st.title("📊 Tableau de Bord Bancaire")
    
    # KPI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Clients Actifs", db.count_active_clients(), "+5%")
    with col2:
        st.metric("Transactions Journalières", db.count_daily_transactions(), "12%")
    with col3:
        st.metric("Dépôts Totaux", f"${db.total_deposits():,.2f}", "8%")
    with col4:
        st.metric("Retraits Totaux", f"${db.total_withdrawals():,.2f}", "3%")
    
    # Graphiques
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dépôts vs Retraits (7 jours)")
        df_trans = pd.DataFrame(db.get_last_week_transactions())
        if not df_trans.empty:
            fig = px.bar(df_trans, x="date", y=["deposit", "withdrawal"], 
                        barmode="group", color_discrete_sequence=["#4CAF50", "#F44336"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Pas de transactions disponibles pour les 7 derniers jours.")

    with col2:
        st.subheader("Répartition des Clients par Type")
        data = db.get_clients_by_type()
        df_clients = pd.DataFrame(data)

        if not df_clients.empty:
            if len(df_clients.columns) == 2:
                df_clients.columns = ["Type de Client", "count"]

            fig = px.pie(df_clients, values="count", names="Type de Client", 
                        color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Pas de données clients disponibles.")

    # Nouveau graphique pour les reçus générés
    st.subheader("Reçus Générés (30 derniers jours)")
    
    # Compter les reçus générés (simulation - à adapter avec votre système de stockage)
    receipts_dir = "receipts"
    if os.path.exists(receipts_dir):
        receipt_files = [f for f in os.listdir(receipts_dir) if f.endswith('.pdf')]
        receipt_dates = [datetime.fromtimestamp(os.path.getmtime(os.path.join(receipts_dir, f))) for f in receipt_files]
        
        if receipt_dates:
            df_receipts = pd.DataFrame({
                'date': [d.date() for d in receipt_dates],
                'count': 1
            })
            df_receipts = df_receipts.groupby('date').sum().reset_index()
            
            fig = px.line(df_receipts, x='date', y='count', 
                         title="Nombre de reçus générés par jour",
                         labels={'date': 'Date', 'count': 'Nombre de reçus'},
                         markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Aucun reçu généré dans les 30 derniers jours.")
    else:
        st.warning("Aucun répertoire de reçus trouvé.")

    # Dernières transactions avec barre de recherche
    st.subheader("Dernières Transactions")
    
    # Barre de recherche
    search_query = st.text_input("Rechercher dans les transactions", "")
    
    transactions = db.get_recent_transactions(50)  # On charge plus de transactions pour la recherche
    if transactions:
        df_transactions = pd.DataFrame(transactions)
        
        # Filtrage basé sur la recherche
        if search_query:
            mask = df_transactions.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
            df_transactions = df_transactions[mask]
        
        st.dataframe(df_transactions, use_container_width=True, hide_index=True)
    else:
        st.warning("Aucune transaction trouvée.")

# Page Gestion Clients
elif selected == "Gestion Clients":
    st.title("👥 Gestion des Clients")
    
    tab1, tab2, tab3 = st.tabs(["Liste Clients", "Ajouter Client", "Modifier Client"])
    
    with tab1:
        st.subheader("Liste des Clients")
        
        # Barre de recherche
        search_query = st.text_input("Rechercher un client", "")
        
        clients = db.get_all_clients()
        if clients:
            df = pd.DataFrame(clients)
            
            # Filtrage basé sur la recherche
            if search_query:
                mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                df = df[mask]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("Aucun client trouvé.")
    
    with tab2:
        st.subheader("Ajouter un Nouveau Client")
        with st.form("add_client_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("Prénom")
                last_name = st.text_input("Nom")
                email = st.text_input("Email")
            with col2:
                phone = st.text_input("Téléphone")
                client_type = st.selectbox("Type de Client", ["Particulier", "Entreprise", "VIP"])
                status = st.selectbox("Statut", ["Actif", "Inactif"])
            
            if st.form_submit_button("Ajouter Client"):
                client_id = db.add_client(
                    first_name, last_name, email, phone, client_type, status
                )
                st.success(f"Client ajouté avec succès! ID: {client_id}")
    
    with tab3:
        st.subheader("Modifier un Client Existant")
        clients = db.get_all_clients()
        if clients:
            # Barre de recherche pour trouver un client
            search_query = st.text_input("Rechercher un client à modifier", "")
            
            if search_query:
                filtered_clients = [c for c in clients if search_query.lower() in f"{c['first_name']} {c['last_name']}".lower()]
            else:
                filtered_clients = clients
                
            client_options = {f"{c['first_name']} {c['last_name']} (ID: {c['id']})": c['id'] for c in filtered_clients}
            selected_client = st.selectbox("Sélectionner un Client", options=list(client_options.keys()))
            
            if selected_client:
                client_id = client_options[selected_client]
                client_data = db.get_client_by_id(client_id)
                
                with st.form("update_client_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_first_name = st.text_input("Prénom", value=client_data['first_name'])
                        new_last_name = st.text_input("Nom", value=client_data['last_name'])
                        new_email = st.text_input("Email", value=client_data['email'])
                    with col2:
                        new_phone = st.text_input("Téléphone", value=client_data['phone'])
                        new_client_type = st.selectbox("Type de Client", 
                                                     ["Particulier", "Entreprise", "VIP"],
                                                     index=["Particulier", "Entreprise", "VIP"].index(client_data['type']))
                        new_status = st.selectbox("Statut", 
                                                ["Actif", "Inactif"],
                                                index=["Actif", "Inactif"].index(client_data['status']))
                    
                    if st.form_submit_button("Mettre à Jour"):
                        db.update_client(
                            client_id, new_first_name, new_last_name, 
                            new_email, new_phone, new_client_type, new_status
                        )
                        st.success("Client mis à jour avec succès!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.warning("Aucun client à modifier.")

# Page Gestion IBAN
elif selected == "Gestion IBAN":
    st.title("💳 Gestion des IBAN")
    
    tab1, tab2 = st.tabs(["Liste IBAN", "Associer IBAN"])
    
    with tab1:
        st.subheader("Liste des Comptes IBAN")
        
        # Barre de recherche
        search_query = st.text_input("Rechercher un compte IBAN", "")
        
        ibans = db.get_all_ibans()
        if ibans:
            df = pd.DataFrame(ibans)
            
            # Filtrage basé sur la recherche
            if search_query:
                mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                df = df[mask]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("Aucun IBAN trouvé.")
    
    with tab2:
        st.subheader("Associer un IBAN à un Client")
        clients = db.get_all_clients()
        if clients:
            # Barre de recherche pour trouver un client
            search_query = st.text_input("Rechercher un client", "")
            
            if search_query:
                filtered_clients = [c for c in clients if search_query.lower() in f"{c['first_name']} {c['last_name']}".lower()]
            else:
                filtered_clients = clients
                
            client_options = {f"{c['first_name']} {c['last_name']} (ID: {c['id']})": c['id'] for c in filtered_clients}
            selected_client = st.selectbox("Sélectionner un Client", options=list(client_options.keys()))
            
            if selected_client:
                client_id = client_options[selected_client]
                
                with st.form("add_iban_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        # Bouton pour générer un nouvel IBAN
                        if st.button("Générer un nouvel IBAN"):
                            st.session_state.new_iban = generate_iban()
                            st.session_state.new_account = generate_account_number()
                        
                        iban = st.text_input("IBAN", 
                                           value=st.session_state.get('new_iban', generate_iban()),
                                           key="iban_input")
                        
                        currency = st.selectbox("Devise", ["EUR", "USD", "GBP"])
                    with col2:
                        account_number = st.text_input("Numéro de compte", 
                                                     value=st.session_state.get('new_account', generate_account_number()),
                                                     key="account_input")
                        account_type = st.selectbox("Type de Compte", ["Courant", "Épargne", "Entreprise"])
                        balance = st.number_input("Solde Initial", min_value=0.0, value=1000.0, step=100.0)
                    
                    if st.form_submit_button("Associer IBAN"):
                        db.add_iban(client_id, iban, currency, account_type, balance)
                        st.success("IBAN associé avec succès!")
        else:
            st.warning("Aucun client disponible. Veuillez d'abord ajouter des clients.")

# Page Transactions
elif selected == "Transactions":
    st.title("⇄ Gestion des Transactions")
    
    tab1, tab2 = st.tabs(["Historique", "Nouvelle Transaction"])
    
    with tab1:
        st.subheader("Historique des Transactions")
        
        # Barre de recherche
        search_query = st.text_input("Rechercher dans les transactions", "")
        
        transactions = db.get_all_transactions()
        if transactions:
            df = pd.DataFrame(transactions)
            
            # Filtrage basé sur la recherche
            if search_query:
                mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                df = df[mask]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("Aucune transaction trouvée.")
    
    with tab2:
        st.subheader("Effectuer une Transaction")
        transaction_type = st.radio("Type de Transaction", ["Dépôt", "Retrait"], horizontal=True)
        
        clients = db.get_all_clients()
        if clients:
            # Barre de recherche pour trouver un client
            search_query = st.text_input("Rechercher un client", "")
            
            if search_query:
                filtered_clients = [c for c in clients if search_query.lower() in f"{c['first_name']} {c['last_name']}".lower()]
            else:
                filtered_clients = clients
                
            client_options = {f"{c['first_name']} {c['last_name']} (ID: {c['id']})": c['id'] for c in filtered_clients}
            selected_client = st.selectbox("Sélectionner un Client", options=list(client_options.keys()))
            
            if selected_client:
                client_id = client_options[selected_client]
                client_ibans = db.get_ibans_by_client(client_id)
                
                if client_ibans:
                    iban_options = {i['iban']: i['id'] for i in client_ibans}
                    selected_iban = st.selectbox("Sélectionner un IBAN", options=list(iban_options.keys()))
                    
                    with st.form("transaction_form"):
                        amount = st.number_input("Montant", min_value=0.01, value=100.0, step=50.0)
                        description = st.text_area("Description")
                        
                        if st.form_submit_button("Exécuter la Transaction"):
                            iban_id = iban_options[selected_iban]
                            if transaction_type == "Dépôt":
                                db.deposit(iban_id, amount, description)
                                st.success(f"Dépôt de ${amount:,.2f} effectué avec succès!")
                            else:
                                # Vérifier le solde avant retrait
                                iban_data = next(i for i in client_ibans if i['id'] == iban_id)
                                if iban_data['balance'] >= amount:
                                    db.withdraw(iban_id, amount, description)
                                    st.success(f"Retrait de ${amount:,.2f} effectué avec succès!")
                                else:
                                    st.error("Solde insuffisant pour effectuer ce retrait.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("Ce client n'a aucun IBAN associé.")
        else:
            st.warning("Aucun client disponible. Veuillez d'abord ajouter des clients.")

# Page Générer Reçu
elif selected == "Générer Reçu":
    st.title("🧾 Générer un Reçu")
    
    # Statistiques des reçus générés
    receipts_dir = "receipts"
    if os.path.exists(receipts_dir):
        receipt_count = len([f for f in os.listdir(receipts_dir) if f.endswith('.pdf')])
        st.metric("Total des reçus générés", receipt_count)
    
    transactions = db.get_all_transactions()
    if transactions:
        # Barre de recherche pour trouver une transaction
        search_query = st.text_input("Rechercher une transaction", "")
        
        if search_query:
            filtered_transactions = [t for t in transactions if search_query.lower() in str(t).lower()]
        else:
            filtered_transactions = transactions
            
        transaction_options = {
            f"Transaction #{t['id']} - {t['type']} de ${t['amount']} le {t['date']}": t['id'] 
            for t in filtered_transactions
        }
        selected_transaction = st.selectbox(
            "Sélectionner une Transaction", 
            options=list(transaction_options.keys())
        )
        
        if selected_transaction:
            transaction_id = transaction_options[selected_transaction]
            transaction_data = db.get_transaction_by_id(transaction_id)
            client_data = db.get_client_by_id(transaction_data['client_id'])
            iban_data = db.get_iban_by_id(transaction_data['iban_id'])
            
            # Prévisualisation des données
            with st.expander("Aperçu des Données"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Informations Client")
                    st.write(f"**Nom:** {client_data['first_name']} {client_data['last_name']}")
                    st.write(f"**Email:** {client_data['email']}")
                    st.write(f"**Téléphone:** {client_data['phone']}")
                
                with col2:
                    st.subheader("Détails Transaction")
                    st.write(f"**Type:** {transaction_data['type']}")
                    st.write(f"**Montant:** ${transaction_data['amount']:,.2f}")
                    st.write(f"**Date:** {transaction_data['date']}")
                    st.write(f"**IBAN:** {iban_data['iban']}")
                    st.write(f"**Description:** {transaction_data['description']}")
            
            # Options de personnalisation
            st.subheader("Personnalisation du Reçu")
            with st.form("receipt_form"):
                col1, col2 = st.columns(2)
                with col1:
                    company_name = st.text_input("Nom de la Banque", value="Banque Virtuelle")
                    company_logo = st.file_uploader("Logo de la Banque", type=["png", "jpg"])
                    receipt_title = st.text_input("Titre du Reçu", value="REÇU DE TRANSACTION")
                with col2:
                    additional_notes = st.text_area("Notes Additionnelles", 
                                                  value="Merci pour votre confiance.\nPour toute question, contactez-nous à support@banquevirtuelle.com")
                    include_signature = st.checkbox("Inclure une signature", value=True)
                
                if st.form_submit_button("Générer le Reçu"):
                    # Chemin temporaire pour le logo
                    logo_path = "assets/logo.png"
                    if company_logo:
                        with open(logo_path, "wb") as f:
                            f.write(company_logo.getbuffer())
                    
                    # Générer le PDF
                    pdf_path = generate_receipt_pdf(
                        transaction_data=transaction_data,
                        client_data=client_data,
                        iban_data=iban_data,
                        company_name=company_name,
                        logo_path=logo_path if company_logo else None,
                        receipt_title=receipt_title,
                        additional_notes=additional_notes,
                        include_signature=include_signature
                    )
                    
                    # Téléchargement du PDF
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()
                    b64 = base64.b64encode(pdf_data).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64}" download="receipt_{transaction_id}.pdf">Télécharger le Reçu</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # Aperçu du PDF
                    st.success("Reçu généré avec succès!")
                    st.write("Aperçu du reçu (les couleurs et polices peuvent varier dans le PDF final):")
                    
                    # Simulation d'aperçu
                    with st.container():
                        st.markdown(f"""
                        <div class="receipt-preview">
                            <div class="receipt-header">
                                <h1>{company_name}</h1>
                                {f'<img src="data:image/png;base64,{base64.b64encode(company_logo.getvalue()).decode()}" class="receipt-logo">' if company_logo else ''}
                                <h2>{receipt_title}</h2>
                            </div>
                            <div class="receipt-body">
                                <div class="receipt-section">
                                    <h3>Informations Client</h3>
                                    <p><strong>Nom:</strong> {client_data['first_name']} {client_data['last_name']}</p>
                                    <p><strong>IBAN:</strong> {iban_data['iban']}</p>
                                </div>
                                <div class="receipt-section">
                                    <h3>Détails de la Transaction</h3>
                                    <p><strong>Type:</strong> {transaction_data['type']}</p>
                                    <p><strong>Montant:</strong> ${transaction_data['amount']:,.2f}</p>
                                    <p><strong>Date:</strong> {transaction_data['date']}</p>
                                    <p><strong>Référence:</strong> {transaction_id}</p>
                                </div>
                                <div class="receipt-notes">
                                    <p>{additional_notes.replace('\n', '<br>')}</p>
                                </div>
                                {'''<div class="receipt-signature">
                                    <p>Signature</p>
                                    <div class="signature-line"></div>
                                </div>''' if include_signature else ''}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.warning("Aucune transaction disponible pour générer un reçu.")