import streamlit as st
import hashlib
from database import BankDatabase, UserManager
from mysql_config import MySQLDatabase

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db_connection():
    try:
        db = BankDatabase()
        if not db.conn:
            st.error("Échec de la connexion à la base de données Railway")
            st.stop()
        return db
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données: {str(e)}")
        st.stop()

def show_login_form():
    with st.form("Login"):
        st.subheader("Connexion")
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit_button = st.form_submit_button("Se connecter")

        if submit_button:
            db = init_db_connection()
            user_manager = UserManager(db.conn)
            hashed_password = hash_password(password)
            user = user_manager.verify_user(username, hashed_password)
            
            if user:
                st.session_state['authenticated'] = True
                st.session_state['user'] = user
                st.success("Connexion réussie!")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect")
            db.close()

def show_signup_form():
    with st.form("Signup"):
        st.subheader("Créer un compte")
        username = st.text_input("Choisissez un nom d'utilisateur")
        email = st.text_input("Email")
        password = st.text_input("Choisissez un mot de passe", type="password")
        confirm_password = st.text_input("Confirmez le mot de passe", type="password")
        submit_button = st.form_submit_button("S'inscrire")

        if submit_button:
            if password != confirm_password:
                st.error("Les mots de passe ne correspondent pas")
                return

            db = init_db_connection()
            user_manager = UserManager(db.conn)
            hashed_password = hash_password(password)
            
            if user_manager.get_user_by_username(username):
                st.error("Ce nom d'utilisateur est déjà pris")
                db.close()
                return

            user_id = user_manager.add_user(username, email, hashed_password)
            db.close()
            
            if user_id:
                st.success("Compte créé avec succès! Vous pouvez maintenant vous connecter.")
            else:
                st.error("Erreur lors de la création du compte")

def show_auth_page():
    st.title("Authentification")
    tab1, tab2 = st.tabs(["Connexion", "Inscription"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_signup_form()

def check_authentication():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if not st.session_state['authenticated']:
        show_auth_page()
        st.stop()

# Exemple d'utilisation dans votre application
def main():
    check_authentication()
    
    # Le reste de votre application ici
    st.title("Tableau de bord bancaire")
    st.write(f"Bienvenue, {st.session_state['user']['username']}!")

if __name__ == "__main__":
    main()