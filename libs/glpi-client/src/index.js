import { GLPIClient } from './glpi-client.js';
import { validateConfig } from './config.js';

/**
 * Script principal de demostración.
 * Muestra cómo usar GLPIClient para interactuar con GLPI.
 */
async function main() {
  console.log('');
  console.log('╔══════════════════════════════════════════════╗');
  console.log('║        AS_GLPITALk — GLPI API Client        ║');
  console.log('╚══════════════════════════════════════════════╝');
  console.log('');

  // ── Validar configuración ──────────────────────────────────
  const { valid, errors } = validateConfig();
  if (!valid) {
    console.error('❌ Configuración incompleta:');
    errors.forEach((e) => console.error(`   → ${e}`));
    console.log('');
    console.log('📝 Edita el archivo .env con los tokens obtenidos de GLPI.');
    console.log('   Guía: Setup > General > API en la interfaz web de GLPI.');
    process.exit(1);
  }

  const client = new GLPIClient();

  try {
    // ── 1. Iniciar sesión ──────────────────────────────────────
    await client.initSession();

    // ── 2. Obtener info de sesión ──────────────────────────────
    const session = await client.getFullSession();
    console.log('');
    console.log('👤 Sesión activa:');
    console.log(`   Usuario: ${session.session?.glpiname || 'N/A'}`);
    console.log(`   Perfil:  ${session.session?.glpiactiveprofile?.name || 'N/A'}`);
    console.log('');

    // ── 3. Listar tickets existentes ────────────────────────────
    console.log('📋 Obteniendo tickets...');
    try {
      const tickets = await client.getTickets({ range: '0-4' });
      if (Array.isArray(tickets) && tickets.length > 0) {
        console.log(`   Encontrados: ${tickets.length} ticket(s)`);
        tickets.forEach((t) => {
          const status = ['', 'Nuevo', 'Asignado', 'Planificado', 'Pendiente', 'Resuelto', 'Cerrado'];
          console.log(`   [#${t.id}] ${t.name} — ${status[t.status] || t.status}`);
        });
      } else {
        console.log('   No hay tickets aún.');
      }
    } catch (err) {
      console.log(`   ⚠️  ${err.message}`);
    }
    console.log('');

    // ── 4. Crear un ticket de prueba ────────────────────────────
    console.log('🎫 Creando ticket de prueba...');
    const newTicket = await client.createTicket({
      name: 'Ticket de prueba — AS_GLPITALk',
      content: '<p>Este ticket fue creado automáticamente desde el API Client de AS_GLPITALk para verificar la conexión.</p>',
      urgency: 3,
      type: 1, // Incidente
    });

    const ticketId = newTicket?.id;
    if (ticketId) {
      console.log(`   ✅ Ticket creado con ID: #${ticketId}`);
    } else {
      console.log('   ✅ Ticket creado:', JSON.stringify(newTicket));
    }
    console.log('');

    // ── 5. Listar computadores ──────────────────────────────────
    console.log('💻 Obteniendo computadores...');
    try {
      const computers = await client.getComputers({ range: '0-4' });
      if (Array.isArray(computers) && computers.length > 0) {
        console.log(`   Encontrados: ${computers.length} computador(es)`);
        computers.forEach((c) => {
          console.log(`   [#${c.id}] ${c.name}`);
        });
      } else {
        console.log('   No hay computadores registrados.');
      }
    } catch (err) {
      console.log(`   ⚠️  ${err.message}`);
    }
    console.log('');

    // ── 6. Listar usuarios ──────────────────────────────────────
    console.log('👥 Obteniendo usuarios...');
    try {
      const users = await client.getUsers({ range: '0-4' });
      if (Array.isArray(users) && users.length > 0) {
        console.log(`   Encontrados: ${users.length} usuario(s)`);
        users.forEach((u) => {
          console.log(`   [#${u.id}] ${u.name} — ${u.realname || ''} ${u.firstname || ''}`);
        });
      } else {
        console.log('   No hay usuarios.');
      }
    } catch (err) {
      console.log(`   ⚠️  ${err.message}`);
    }

    console.log('');
    console.log('🎉 ¡Conexión con GLPI exitosa!');

  } catch (err) {
    console.error('');
    console.error('❌ Error:', err.message);
    console.error('');
    console.error('Posibles causas:');
    console.error('  1. GLPI no está corriendo (docker compose up -d)');
    console.error('  2. Los tokens en .env son incorrectos');
    console.error('  3. La API REST no está habilitada en GLPI');
    console.error('  4. El API Client no tiene los permisos de IP correctos');
  } finally {
    // ── Siempre cerrar sesión ──────────────────────────────────
    await client.killSession();
    console.log('');
  }
}

main();
