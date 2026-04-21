import config from './config.js';

/**
 * Script rápido para verificar que GLPI está accesible
 * antes de intentar usar la API completa.
 */
async function testConnection() {
  console.log('');
  console.log('🔍 Test de conexión a GLPI...');
  console.log(`   URL: ${config.glpiUrl}`);
  console.log(`   API: ${config.apiUrl}`);
  console.log('');

  // ── Test 1: GLPI está vivo ───────────────────────────────
  try {
    console.log('1️⃣  Verificando que GLPI responde...');
    const res = await fetch(config.glpiUrl, {
      signal: AbortSignal.timeout(5000),
    });
    console.log(`   ✅ GLPI responde con status: ${res.status}`);
  } catch (err) {
    console.error(`   ❌ GLPI no responde: ${err.message}`);
    console.error('   → Verifica que los contenedores estén corriendo:');
    console.error('     docker compose up -d');
    process.exit(1);
  }

  // ── Test 2: API endpoint accesible ────────────────────────
  try {
    console.log('2️⃣  Verificando endpoint de API...');
    const res = await fetch(config.apiUrl, {
      signal: AbortSignal.timeout(5000),
    });
    const data = await res.json();
    console.log(`   ✅ API accesible. Versión GLPI: ${data?.version || 'desconocida'}`);
  } catch (err) {
    console.error(`   ❌ API no accesible: ${err.message}`);
    console.error('   → Verifica que la API REST esté habilitada en GLPI:');
    console.error('     Setup > General > API > Enable REST API = Yes');
    process.exit(1);
  }

  // ── Test 3: Autenticación (si hay tokens) ─────────────────
  if (config.appToken && config.appToken !== 'tu_app_token_aqui') {
    try {
      console.log('3️⃣  Verificando autenticación...');
      const res = await fetch(`${config.apiUrl}/initSession`, {
        headers: {
          'Content-Type': 'application/json',
          'App-Token': config.appToken,
          'Authorization': `user_token ${config.userToken}`,
        },
        signal: AbortSignal.timeout(5000),
      });
      const data = await res.json();

      if (data.session_token) {
        console.log('   ✅ Autenticación exitosa!');

        // Cerrar la sesión de prueba
        await fetch(`${config.apiUrl}/killSession`, {
          headers: {
            'Content-Type': 'application/json',
            'App-Token': config.appToken,
            'Session-Token': data.session_token,
          },
        });
      } else {
        console.error(`   ❌ Error de autenticación: ${JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(`   ❌ Error de autenticación: ${err.message}`);
    }
  } else {
    console.log('3️⃣  Autenticación saltada — configura los tokens en .env');
  }

  console.log('');
  console.log('✅ Test de conexión finalizado.');
  console.log('');
}

testConnection();
