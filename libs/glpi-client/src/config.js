import dotenv from 'dotenv';

dotenv.config();

/**
 * Configuración centralizada para la conexión con GLPI API.
 * Los valores se leen desde el archivo .env
 */
const config = {
  // URL base de GLPI (sin trailing slash)
  glpiUrl: process.env.GLPI_URL?.replace(/\/+$/, '') || 'http://localhost:8080',

  // Endpoint de la API REST
  get apiUrl() {
    return `${this.glpiUrl}/apirest.php`;
  },

  // Tokens de autenticación
  appToken: process.env.GLPI_APP_TOKEN || '',
  userToken: process.env.GLPI_USER_TOKEN || '',

  // Configuración de requests
  requestTimeout: 10000, // 10 segundos
};

/**
 * Valida que la configuración esencial esté presente.
 * @returns {{ valid: boolean, errors: string[] }}
 */
export function validateConfig() {
  const errors = [];

  if (!config.appToken || config.appToken === 'tu_app_token_aqui') {
    errors.push('GLPI_APP_TOKEN no está configurado en .env');
  }
  if (!config.userToken || config.userToken === 'tu_user_token_aqui') {
    errors.push('GLPI_USER_TOKEN no está configurado en .env');
  }
  if (!config.glpiUrl) {
    errors.push('GLPI_URL no está configurado en .env');
  }

  return { valid: errors.length === 0, errors };
}

export default config;
