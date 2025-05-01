import mysql.connector
from mysql.connector import pooling, Error
import os
from dotenv import load_dotenv
import logging
import time
from typing import Optional, Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('db_errors.log')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class MySQLDatabase:
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        """Initialise la connexion avec reprise automatique"""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.pool = None
        self._initialize()

    def _get_validated_config(self) -> Dict[str, Any]:
        """Valide et retourne la configuration de connexion"""
        config = {
            'host': os.getenv("MYSQL_HOST"),
            'port': self._parse_port(os.getenv("MYSQL_PORT", "3306")),
            'database': os.getenv("MYSQL_DATABASE"),
            'user': os.getenv("MYSQL_USER"),
            'password': os.getenv("MYSQL_PASSWORD"),
            'ssl_disabled': True,  # Railway nécessite SSL
            'ssl_ca': '/etc/ssl/cert.pem',
            'connect_timeout': 20,
            'auth_plugin': 'mysql_native_password',
            'pool_name': 'railway_pool',
            'pool_size': 5
        }

        missing = [k for k, v in config.items() if not v and k not in ['ssl_ca', 'pool_name', 'pool_size']]
        if missing:
            raise ValueError(f"Configuration manquante: {', '.join(missing)}")

        logger.info(f"Configuration validée pour {config['user']}@{config['host']}:{config['port']}")
        return config

    def _parse_port(self, port_str: str) -> int:
        """Convertit et valide le numéro de port"""
        try:
            port = int(port_str)
            if not (0 < port <= 65535):
                raise ValueError(f"Port {port} hors plage valide")
            return port
        except ValueError as e:
            logger.warning(f"Port invalide '{port_str}', utilisation du port par défaut 3306")
            return 3306

    def _initialize(self):
        """Établit la connexion avec mécanisme de reprise"""
        config = self._get_validated_config()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self.pool = pooling.MySQLConnectionPool(**config)
                
                # Test de connexion immédiat
                with self._test_connection() as conn:
                    logger.info(f"Connexion établie (tentative {attempt}/{self.max_retries})")
                
                return  # Succès - sortie de la boucle
                
            except Exception as e:
                self._handle_connection_error(attempt, e)
        
        raise RuntimeError(f"Échec après {self.max_retries} tentatives")

    def _test_connection(self):
        """Teste la connexion avec ping"""
        conn = self.pool.get_connection()
        try:
            conn.ping(reconnect=True, attempts=3, delay=1)
            return conn
        except Exception:
            conn.close()
            raise

    def _handle_connection_error(self, attempt: int, error: Exception):
        """Gère les erreurs de connexion"""
        error_msg = self._format_error(error)
        logger.warning(f"Tentative {attempt}/{self.max_retries} échouée: {error_msg}")
        
        if attempt < self.max_retries:
            time.sleep(self.retry_delay * attempt)  # Backoff exponentiel
            if self.pool:
                self.pool.closeall()

    def _format_error(self, error: Exception) -> str:
        """Formatte les messages d'erreur de manière cohérente"""
        if isinstance(error, Error):
            return getattr(error, 'msg', str(error))
        return str(error)

    def get_connection(self):
        """Obtient une connexion active avec gestion d'erreur"""
        if not self.pool:
            raise RuntimeError("Pool de connexions non initialisé")
            
        try:
            conn = self.pool.get_connection()
            conn.ping(reconnect=True)
            return conn
        except Exception as e:
            logger.error(f"Échec d'obtention de connexion: {self._format_error(e)}")
            raise ConnectionError("Échec de connexion à la base de données") from e

    def close(self):
        """Ferme toutes les connexions proprement"""
        if self.pool:
            try:
                self.pool.closeall()
                logger.info("Pool de connexions fermé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture: {str(e)}")

def get_database() -> MySQLDatabase:
    """Factory pour obtenir une instance de base de données"""
    try:
        db = MySQLDatabase(max_retries=5, retry_delay=3)  # Augmentation des tentatives
        logger.info("Connexion à la base de données établie avec succès")
        return db
    except Exception as e:
        logger.critical(f"Échec critique d'initialisation: {str(e)}")
        raise RuntimeError("Service de base de données indisponible") from e