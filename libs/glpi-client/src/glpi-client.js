import config from './config.js';

/**
 * Cliente para la API REST de GLPI.
 * Maneja autenticación, sesiones, y operaciones CRUD sobre recursos GLPI.
 *
 * @example
 * ```js
 * const client = new GLPIClient();
 * await client.initSession();
 * const tickets = await client.getTickets();
 * await client.killSession();
 * ```
 */
export class GLPIClient {
  constructor() {
    this.apiUrl = config.apiUrl;
    this.appToken = config.appToken;
    this.userToken = config.userToken;
    this.sessionToken = null;
  }

  // ─── Helpers internos ───────────────────────────────────────

  /**
   * Construye los headers base para las peticiones.
   * @returns {Object} Headers con App-Token y, si existe, Session-Token.
   */
  _getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
      'App-Token': this.appToken,
    };

    if (this.sessionToken) {
      headers['Session-Token'] = this.sessionToken;
    }

    return headers;
  }

  /**
   * Realiza una petición HTTP genérica a la API de GLPI.
   * @param {string} endpoint - Ruta relativa (e.g., '/Ticket')
   * @param {Object} options - Opciones adicionales de fetch
   * @returns {Promise<Object>} Respuesta JSON del servidor
   */
  async _request(endpoint, options = {}) {
    const url = `${this.apiUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this._getHeaders(),
        ...options.headers,
      },
      signal: AbortSignal.timeout(config.requestTimeout),
    });

    // Manejar respuestas vacías (204 No Content)
    if (response.status === 204) {
      return null;
    }

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = Array.isArray(data)
        ? data[1] || data[0]
        : data.message || JSON.stringify(data);
      throw new Error(
        `GLPI API Error [${response.status}]: ${errorMsg}`
      );
    }

    return data;
  }

  // ─── Gestión de sesión ──────────────────────────────────────

  /**
   * Inicia una sesión con GLPI usando User-Token.
   * Debe llamarse antes de cualquier otra operación.
   * @returns {Promise<string>} El session_token obtenido.
   */
  async initSession() {
    console.log('🔐 Iniciando sesión con GLPI...');

    const response = await this._request('/initSession', {
      method: 'GET',
      headers: {
        Authorization: `user_token ${this.userToken}`,
      },
    });

    this.sessionToken = response.session_token;
    console.log('✅ Sesión iniciada correctamente.');
    return this.sessionToken;
  }

  /**
   * Cierra la sesión activa con GLPI.
   * Siempre llamar al finalizar para liberar recursos.
   */
  async killSession() {
    if (!this.sessionToken) {
      console.log('⚠️  No hay sesión activa para cerrar.');
      return;
    }

    try {
      await this._request('/killSession', { method: 'GET' });
      console.log('🔓 Sesión cerrada correctamente.');
    } finally {
      this.sessionToken = null;
    }
  }

  /**
   * Obtiene información de la sesión activa (usuario, perfil, etc.).
   * @returns {Promise<Object>} Datos de la sesión actual.
   */
  async getFullSession() {
    return this._request('/getFullSession');
  }

  // ─── Operaciones CRUD genéricas ─────────────────────────────

  /**
   * Obtiene una lista de items de un tipo determinado.
   * @param {string} itemType - Tipo de recurso GLPI (e.g., 'Ticket', 'Computer')
   * @param {Object} params - Parámetros de búsqueda (range, sort, etc.)
   * @returns {Promise<Array>} Lista de items.
   */
  async getItems(itemType, params = {}) {
    const query = new URLSearchParams(params).toString();
    const endpoint = `/${itemType}${query ? '?' + query : ''}`;
    return this._request(endpoint);
  }

  /**
   * Obtiene un item específico por su ID.
   * @param {string} itemType - Tipo de recurso GLPI
   * @param {number} id - ID del item
   * @returns {Promise<Object>} Datos del item.
   */
  async getItem(itemType, id) {
    return this._request(`/${itemType}/${id}`);
  }

  /**
   * Crea un nuevo item en GLPI.
   * @param {string} itemType - Tipo de recurso GLPI
   * @param {Object} data - Datos del item a crear
   * @returns {Promise<Object>} Respuesta con el ID del item creado.
   */
  async createItem(itemType, data) {
    return this._request(`/${itemType}`, {
      method: 'POST',
      body: JSON.stringify({ input: data }),
    });
  }

  /**
   * Actualiza un item existente en GLPI.
   * @param {string} itemType - Tipo de recurso GLPI
   * @param {number} id - ID del item
   * @param {Object} data - Datos a actualizar
   * @returns {Promise<Object>} Respuesta de la actualización.
   */
  async updateItem(itemType, id, data) {
    return this._request(`/${itemType}/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ input: data }),
    });
  }

  /**
   * Elimina un item de GLPI.
   * @param {string} itemType - Tipo de recurso GLPI
   * @param {number} id - ID del item
   * @param {boolean} purge - Si true, elimina permanentemente; si false, envía a papelera.
   * @returns {Promise<Object>} Respuesta de la eliminación.
   */
  async deleteItem(itemType, id, purge = false) {
    const query = purge ? '?force_purge=1' : '';
    return this._request(`/${itemType}/${id}${query}`, {
      method: 'DELETE',
      body: JSON.stringify({ input: { id }, force_purge: purge }),
    });
  }

  // ─── Métodos de conveniencia: Tickets ───────────────────────

  /**
   * Obtiene la lista de tickets.
   * @param {Object} params - Filtros opcionales
   * @returns {Promise<Array>} Lista de tickets.
   */
  async getTickets(params = {}) {
    return this.getItems('Ticket', params);
  }

  /**
   * Obtiene un ticket específico.
   * @param {number} id - ID del ticket
   * @returns {Promise<Object>} Datos del ticket.
   */
  async getTicket(id) {
    return this.getItem('Ticket', id);
  }

  /**
   * Crea un nuevo ticket.
   * @param {Object} ticketData - Datos del ticket
   * @param {string} ticketData.name - Título del ticket
   * @param {string} ticketData.content - Descripción del ticket
   * @param {number} [ticketData.urgency] - Urgencia (1-5)
   * @param {number} [ticketData.priority] - Prioridad (1-6)
   * @param {number} [ticketData.type] - Tipo: 1=Incidente, 2=Solicitud
   * @returns {Promise<Object>} Respuesta con el ID del ticket creado.
   */
  async createTicket(ticketData) {
    const data = {
      name: ticketData.name || 'Sin título',
      content: ticketData.content || '',
      urgency: ticketData.urgency || 3,
      priority: ticketData.priority || 3,
      type: ticketData.type || 1, // 1 = Incidente
      ...ticketData,
    };
    return this.createItem('Ticket', data);
  }

  /**
   * Actualiza un ticket existente.
   * @param {number} id - ID del ticket
   * @param {Object} data - Campos a actualizar
   * @returns {Promise<Object>} Respuesta de la actualización.
   */
  async updateTicket(id, data) {
    return this.updateItem('Ticket', id, data);
  }

  /**
   * Elimina un ticket.
   * @param {number} id - ID del ticket
   * @param {boolean} purge - Eliminación permanente
   * @returns {Promise<Object>} Respuesta.
   */
  async deleteTicket(id, purge = false) {
    return this.deleteItem('Ticket', id, purge);
  }

  // ─── Métodos de conveniencia: Computadores ──────────────────

  /**
   * Obtiene la lista de computadores registrados en GLPI.
   * @param {Object} params - Filtros opcionales
   * @returns {Promise<Array>} Lista de computadores.
   */
  async getComputers(params = {}) {
    return this.getItems('Computer', params);
  }

  /**
   * Obtiene un computador específico.
   * @param {number} id - ID del computador
   * @returns {Promise<Object>} Datos del computador.
   */
  async getComputer(id) {
    return this.getItem('Computer', id);
  }

  // ─── Métodos de conveniencia: Usuarios ──────────────────────

  /**
   * Obtiene la lista de usuarios.
   * @param {Object} params - Filtros opcionales
   * @returns {Promise<Array>} Lista de usuarios.
   */
  async getUsers(params = {}) {
    return this.getItems('User', params);
  }

  /**
   * Obtiene un usuario específico.
   * @param {number} id - ID del usuario
   * @returns {Promise<Object>} Datos del usuario.
   */
  async getUser(id) {
    return this.getItem('User', id);
  }

  // ─── Búsqueda ───────────────────────────────────────────────

  /**
   * Realiza una búsqueda en GLPI.
   * @param {string} itemType - Tipo de recurso a buscar
   * @param {Object} criteria - Criterios de búsqueda
   * @returns {Promise<Object>} Resultados de búsqueda con totalcount y datos.
   */
  async search(itemType, criteria = {}) {
    const params = new URLSearchParams();

    if (criteria.criteria) {
      criteria.criteria.forEach((c, i) => {
        Object.keys(c).forEach((key) => {
          params.append(`criteria[${i}][${key}]`, c[key]);
        });
      });
    }

    if (criteria.range) {
      params.append('range', criteria.range);
    }

    if (criteria.sort) {
      params.append('sort', criteria.sort);
    }

    if (criteria.order) {
      params.append('order', criteria.order);
    }

    const endpoint = `/search/${itemType}?${params.toString()}`;
    return this._request(endpoint);
  }
}

export default GLPIClient;
