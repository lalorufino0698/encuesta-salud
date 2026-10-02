(() => {
  const section = document.createElement('section');
  section.id = 'ad-registration'; section.hidden = true;
  section.innerHTML = `<div class="eyebrow">02 / REVISIÓN Y REGISTRO</div><h2>Revisa la información extraída</h2>
  <p id="ad-explanation">Al pulsar Sí se registrará la persona en Active Directory: se comprobará el usuario, se generará su contraseña y se asignarán la OU y el grupo según el área.</p>
  <label for="ad-person">Persona</label><select id="ad-person"></select><dl id="ad-summary"></dl>
  <div id="sgd-validation" hidden aria-live="polite"></div><p id="ad-status" role="status" aria-live="polite"></p>
  <button type="button" id="ad-yes" class="btn-primary">Sí, la información es correcta — registrar</button>
  <button type="button" id="ad-no" class="btn-secondary">No, corregir información</button>
  <form id="ad-corrections" hidden><h3>Ajustar acceso de Dominio</h3><p id="ad-correction-scope"></p><p id="ad-correction-person"></p>
  <label for="ad-user">Usuario alternativo (solo si es necesario)</label><input id="ad-user" maxlength="20" pattern="[a-z][a-z0-9._-]{0,19}" placeholder="Se genera automáticamente">
  <label for="ad-group">Grupo (solo si no se resuelve por el área)</label><select id="ad-group"><option value="">Resolver automáticamente</option></select>
  <label for="ad-ou">OU de CAFED (solo si no se resuelve por el área)</label><select id="ad-ou"><option value="">Resolver automáticamente</option></select>
  <button type="submit" class="btn-primary">Guardar correcciones</button></form>
  <div id="ad-tracking" hidden><h3>Estado del registro</h3><ol id="ad-progress" aria-live="polite"></ol>
  <details class="technical"><summary>Ver detalle de las operaciones</summary><ol id="ad-log"></ol></details></div>
  <button type="button" id="ad-resume" class="btn-primary" hidden>Retomar seguimiento</button>
  <div id="ad-credentials" hidden>
  <div class="registration-success" role="status" aria-live="polite"><span class="registration-success-icon" aria-hidden="true">✓</span><div><span class="eyebrow">REGISTRO EXITOSO · DOMINIO</span><h2>Usuario de Dominio registrado correctamente</h2><p>La creación de la cuenta ha finalizado. Estas son sus credenciales de acceso.</p></div></div>
  <div id="ad-secret-fields"><h3>Credenciales de acceso a Dominio</h3>
  <label for="ad-created-user">Usuario de Dominio</label><input id="ad-created-user" readonly>
  <label for="ad-created-password">Contraseña generada (Dominio)</label><input id="ad-created-password" readonly autocomplete="off">
  
  <div id="sgd-secret-fields" hidden>
  <h3 style="margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1rem;">Credenciales de acceso a SGD</h3>
  <label for="sgd-created-user">Usuario de SGD</label><input id="sgd-created-user" readonly>
  <label for="sgd-created-password">Contraseña de SGD</label><input id="sgd-created-password" readonly autocomplete="off">
  </div>
  
  <p class="credentials-note">Las credenciales estarán disponibles durante 15 minutos en esta vista. Los registros también se guardan en el historial local al final de la página.</p></div>
  <p id="ad-hidden-notice" hidden>Credenciales ocultas. El registro se completó correctamente.</p>
  <button type="button" id="ad-clear">Ocultar credenciales</button></div>`;
  document.querySelector('main').insertBefore(section, document.querySelector('#result'));
  for (const formId of ['ad-corrections', 'ad-credentials']) {
    const form = document.getElementById(formId);
    for (const label of [...form.querySelectorAll('label')]) {
      const input = label.nextElementSibling, field = document.createElement('div'); field.className = 'field';
      label.parentElement.insertBefore(field, label); field.append(label, input);
    }
  }
  const el = id => document.getElementById('ad-' + id);
  const entry = document.querySelector('#form').closest('section');
  const review = document.createElement('div'); review.id = 'ad-review-view';
  section.insertBefore(review, section.firstChild);
  while (review.nextSibling && review.nextSibling !== el('corrections')) review.append(review.nextSibling);
  review.insertBefore(document.getElementById('sgd-validation'), el('person').previousElementSibling);
  // Status belongs to every view, not only the initial review.
  section.insertBefore(el('status'), review);
  const navigation = document.createElement('div'); navigation.className = 'view-navigation';
  navigation.innerHTML = '<button type="button" id="ad-back">← Volver a la entrada</button><span id="ad-view-label"></span>';
  section.prepend(navigation);
  const finish = document.createElement('div'); finish.className = 'finish-actions';
  finish.innerHTML = '<button type="button" id="ad-another" class="btn-primary">Registrar otra persona</button>';
  el('credentials').append(finish);
  finish.prepend(el('clear'));
  for (const [id, label] of [['created-user', 'Copiar usuario'], ['created-password', 'Copiar contraseña']]) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'copy-button'; button.textContent = label;
    button.onclick = async () => {
      try { await navigator.clipboard.writeText(el(id).value); showToast(id.includes('user') ? 'Usuario copiado.' : 'Contraseña copiada.', 'success'); }
      catch { el(id).focus(); el(id).select(); showToast('No se pudo copiar automáticamente. El texto está seleccionado: utiliza Ctrl+C.', 'error'); }
    };
    el(id).parentElement.append(button);
  }
  for (const [id, label] of [['sgd-created-user', 'Copiar usuario SGD'], ['sgd-created-password', 'Copiar contraseña SGD']]) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'copy-button'; button.textContent = label;
    button.onclick = async () => {
      try { await navigator.clipboard.writeText(document.getElementById(id).value); showToast(id.includes('user') ? 'Usuario copiado.' : 'Contraseña copiada.', 'success'); }
      catch { document.getElementById(id).focus(); document.getElementById(id).select(); showToast('No se pudo copiar automáticamente.', 'error'); }
    };
    const input = document.getElementById(id);
    const field = document.createElement('div'); field.className = 'field';
    input.parentElement.insertBefore(field, input.previousElementSibling);
    field.append(input.previousElementSibling, input, button);
  }
  function view(name) {
    const changed = (document.body.dataset.adView || 'entry') !== name;
    document.body.dataset.adView = name;
    entry.hidden = name !== 'entry'; section.hidden = name === 'entry';
    review.hidden = name !== 'review'; el('corrections').hidden = name !== 'edit';
    el('tracking').hidden = name !== 'progress'; el('credentials').hidden = name !== 'credentials';
    el('back').hidden = busy || name === 'progress';
    el('view-label').textContent = {review:'02 · Revisión',edit:'02 · Corregir datos',progress:'03 · Registro en curso',credentials:'04 · Credenciales'}[name] || '';
    if (changed) window.scrollTo({top:0, behavior:'instant'});
  }
  let source, indices = [], drafts = [], catalog = null, busy = false, pending = null, controls = [], version = 0;
  const current = () => source.usuarios[indices[Number(el('person').value)]];
  const draft = () => drafts[Number(el('person').value)];
  const norm = text => (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const username = d => d.username || (norm(d.given_names).trim()[0] || '') + norm(d.paternal).replace(/[^a-z0-9]/g, '');
  const publish = () => window.dispatchEvent(new CustomEvent('ad-registration-updated', {detail: source}));
  function renderProgress(state) {
    el('tracking').hidden = false;
    const servicios = ['dominio'];
    const stages = [];
    if (servicios.includes('dominio')) {
        stages.push('Preparar usuario', 'Validar en el directorio', 'Generar contraseña', 'Crear cuenta en la OU', 'Asignar grupo', 'Configurar acceso');
    }
    if (servicios.includes('sgd')) {
        stages.push('Validar tabla Ciudadano en SGD', 'Registrar Ciudadano', 'Registrar Empleado y accesos en SGD');
    }
    stages.push('Verificar registro');

    const indexFor = message => {
      const m = norm(message);
      if (/verificando|registro completado|completado/.test(m)) return stages.length - 1;
      let step = 0;
      if (servicios.includes('dominio')) {
          if (/estableciendo|contrasena aceptada|habilitando/.test(m)) step = 5;
          else if (/miembro de|membresia/.test(m)) step = 4;
          else if (/creando el usuario|usuario creado y ubicado/.test(m)) step = 3;
          else if (/generando una|contrasena generada/.test(m)) step = 2;
          else if (/consultando|identificado|identificada|comprobando|validacion completada/.test(m)) step = 1;
      }
      const offset = servicios.includes('dominio') ? 6 : 0;
      if (servicios.includes('sgd')) {
          if (/registro de empleado|iniciando registro|completado con exito/.test(m)) step = offset + 2;
          else if (/registrando ciudadano|ciudadano registrado/.test(m)) step = offset + 1;
          else if (/validando tabla ciudadano|ciudadano existe|ciudadano no existe|preparando acceso|integracion con sgd/.test(m)) step = offset + 0;
      }
      return step;
    };
    const position = Math.max(0, ...state.events.map(indexFor));
    el('progress').replaceChildren(...stages.map((title, index) => {
      const item = document.createElement('li');
      const success = state.done && state.result?.ok;
      item.className = success || index < position ? 'complete' : index === position ? (state.done ? 'failed' : 'active') : 'pending';
      const mark = document.createElement('span'); mark.className = 'step-icon'; mark.textContent = item.className === 'complete' ? '✓' : item.className === 'failed' ? '!' : String(index + 1);
      const label = document.createElement('span'); label.textContent = title;
      const status = document.createElement('small'); status.textContent = item.className === 'complete' ? 'Completado' : item.className === 'active' ? 'En curso' : item.className === 'failed' ? 'Requiere atención' : 'Pendiente';
      item.append(mark, label, status); return item;
    }));
    el('log').replaceChildren(...state.events.map(message => { const item = document.createElement('li'); item.textContent = message; return item; }));
    el('status').textContent = state.done ? (state.result?.ok ? 'El registro ha finalizado exitosamente.' : 'El registro se ha detenido.') : stages[position] + '…';
    el('status').dataset.tone = state.done ? (state.result?.ok ? 'success' : 'error') : 'info';
  }
  async function api(path, body) {
    const options = {headers: {'X-AD-Review': '1'}, cache: 'no-store'};
    if (body) { options.method = 'POST'; options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
    const response = await fetch('/api/registro-ad/' + path, options), result = await response.json();
    if (!response.ok) { const error = new Error(typeof result.detail === 'string' ? result.detail : 'No se pudo procesar la solicitud.'); error.status = response.status; throw error; }
    return result;
  }
  function clearCredentials() { el('credentials').hidden = true; el('created-password').value = ''; el('created-user').value = ''; }
  function lock(value) {
    if (value && !busy) { controls = [...document.querySelector('#form').elements].map(c => [c, c.disabled]); controls.forEach(([c]) => c.disabled = true); }
    else if (!value && busy) controls.forEach(([c, disabled]) => c.disabled = disabled);
    busy = value; for (const id of ['person', 'yes', 'no']) el(id).disabled = value;
    if (value) { el('yes').hidden = true; el('no').hidden = true; }
  }
  function renderSgd(state, user, result) {
    const panel = document.getElementById('sgd-validation');
    const content = {
      loading: ['…', 'VALIDACIÓN EN CURSO', 'Consultando ciudadano', 'Estamos comprobando si el DNI está registrado en SGD.'],
      exists: ['✓', 'CONSULTA COMPLETADA', 'El ciudadano ya existe en SGD', 'El DNI coincide con un ciudadano registrado. No es necesario volver a crearlo.'],
      missing: ['!', 'CONSULTA COMPLETADA', 'El ciudadano no está registrado', 'No encontramos un ciudadano con este DNI en SGD. Será necesario registrarlo antes de crear al empleado.'],
      error: ['!', 'NO SE PUDO COMPLETAR', 'No pudimos verificar el DNI', result?.message || 'Intenta consultar nuevamente.']
    }[state];
    panel.dataset.state = state;
    panel.replaceChildren();
    const hero = document.createElement('div'); hero.className = 'sgd-outcome';
    const icon = document.createElement('span'); icon.className = 'sgd-outcome-icon'; icon.textContent = content[0]; icon.setAttribute('aria-hidden','true');
    const body = document.createElement('div');
    const badge = document.createElement('div'); badge.className = 'sgd-eyebrow'; badge.textContent = content[1];
    const title = document.createElement('h3'); title.textContent = content[2];
    const description = document.createElement('p'); description.textContent = content[3];
    body.append(badge,title,description); hero.append(icon,body); panel.append(hero);
    const steps = document.createElement('ol'); steps.className = 'sgd-steps'; steps.setAttribute('aria-label','Proceso de SGD');
    const finished = state === 'exists' || state === 'missing';
    for (const [number,title,detail,done] of [
      ['1','Información extraída','Datos de la persona disponibles',true],
      ['2','Validación de ciudadano',finished ? 'Consulta finalizada' : state === 'error' ? 'Consulta interrumpida' : 'Consultando tabla Ciudadano…',finished]
    ]) {
      const step = document.createElement('li'); step.className = done ? 'is-done' : 'is-pending';
      const mark = document.createElement('span'); mark.className = 'sgd-step-mark'; mark.textContent = done ? '✓' : number;
      const label = document.createElement('strong'); label.textContent = title;
      const small = document.createElement('span'); small.textContent = detail;
      step.append(mark,label,small); steps.append(step);
    }
    panel.append(steps);
    const future = document.createElement('div'); future.className = 'sgd-future';
    const futureTitle = document.createElement('h4'); futureTitle.textContent = 'Siguientes etapas de SGD';
    const futureIntro = document.createElement('p'); futureIntro.textContent = 'Acciones automatizadas · Al confirmar el registro, se ejecutarán automáticamente las siguientes operaciones en SGD:';
    const planned = document.createElement('ol'); planned.className = 'sgd-planned';
    const stages = [
      ...(state === 'exists' ? [] : [['Registrar ciudadano', state === 'missing' ? 'Necesario antes de continuar: el DNI no está en Ciudadano.' : 'Solo será necesario si la consulta confirma que el ciudadano no existe.']]),
      ['Validar empleado por DNI', 'Comprobar si ya existe como empleado. Si existe, detener el alta para evitar duplicados.'],
      ['Preparar datos laborales y acceso', 'Definir dependencia, cargo, categoría y local. Si se solicita una cuenta, validar el usuario y definir su acceso y roles.'],
      ['Registrar empleado', 'Generar el código de empleado y guardar sus datos personales y laborales.'],
      ['Crear cuenta y asignar roles', 'Solo si se solicita usuario: crear la cuenta, habilitar el acceso al aplicativo y asignar los roles definidos.'],
      ['Configurar permisos especiales', 'Solo si corresponde al perfil autorizado: administración o Mesa de Partes.'],
      ['Confirmar registro', 'Confirmar todos los cambios y mostrar el código de empleado. Si ocurre un error, deshacer los cambios del registro de empleado y sus accesos.']
    ];
    for (const [title, description] of stages) {
      const item = document.createElement('li'), heading = document.createElement('strong'), detail = document.createElement('p'), badge = document.createElement('span');
      heading.textContent = title; detail.textContent = description; badge.textContent = 'Pendiente'; badge.className = 'sgd-pending-badge';
      item.append(heading, badge, detail); planned.append(item);
    }
    future.append(futureTitle, futureIntro, planned); panel.append(future);
    if (draft().servicios_a_crear.includes('dominio')) {
      const identity = document.createElement('p'); identity.className = 'sgd-next';
      const data = user.datos_sgd;
      identity.textContent = `Datos de SGD: ${data.given_names} ${data.paternal} ${data.maternal} · DNI ${data.dni} · Área ${data.area}`;
      panel.append(identity);
    }
    const note = document.createElement('p'); note.className = 'sgd-next';
    note.textContent = finished ? 'Al confirmar el registro, se creará el Empleado y se configurarán sus accesos automáticamente en SGD.' : 'Esta consulta previa no modifica los datos de SGD.';
    panel.append(note);
    const consult = document.createElement('button'); consult.type = 'button'; consult.className = 'btn-secondary'; consult.textContent = 'Volver a consultar un DNI'; consult.disabled = busy; consult.onclick = () => el('back').click(); panel.append(consult);
    if (state === 'error') {
      const retry = document.createElement('button'); retry.type='button'; retry.className='btn-primary'; retry.textContent='Reintentar consulta'; retry.onclick=()=>validateSgd(user, true); panel.append(retry);
    }
  }
  async function validateSgd(user, force = false) {
    const panel = document.getElementById('sgd-validation'), localVersion = version;
    panel.hidden = !(user.servicios_a_crear || []).includes('sgd');
    panel.replaceChildren();
    if (panel.hidden) return;
    if (!force && user.validacion_sgd) { renderSgd(user.validacion_sgd.existe ? 'exists' : 'missing', user); return; }
    const requestId = user.sgdRequestId = (user.sgdRequestId || 0) + 1;
    renderSgd('loading',user);
    try {
      const response = await fetch('/api/sgd/validar-ciudadano', {method:'POST', headers:{'Content-Type':'application/json','X-AD-Review':'1'}, body:JSON.stringify({dni:user.datos_sgd.dni}), cache:'no-store'});
      const result = await response.json();
      if (localVersion !== version || current() !== user || requestId !== user.sgdRequestId) return;
      if (!response.ok) throw new Error(response.status === 404 ? 'El servicio de validación no está disponible. Reinicia la aplicación e inténtalo nuevamente.' : typeof result.detail === 'string' ? result.detail : 'Revisa el DNI: debe tener 8 dígitos.');
      renderSgd(result.existe ? 'exists' : 'missing',user);
      user.validacion_sgd = result; publish();
    } catch (error) {
      if (localVersion !== version || current() !== user || requestId !== user.sgdRequestId) return;
      renderSgd('error',user,error);
    }
  }
  function show() {
    clearCredentials(); el('corrections').hidden = true; el('progress').replaceChildren(); el('tracking').hidden = true; el('status').dataset.tone = 'info';
    const user = current(), d = draft().servicios_a_crear.includes('dominio') ? draft() : user.datos_sgd; el('summary').replaceChildren();
    el('yes').hidden = false; el('no').hidden = false;
    for (const [name, value] of [['Apellidos', [d.paternal, d.maternal].filter(Boolean).join(' ')], ['Nombres', d.given_names], ['DNI', d.dni], ['Área', d.area], ...(draft().servicios_a_crear.includes('dominio') ? [['Usuario de dominio propuesto', username(d)]] : [])]) {
      const label = document.createElement('dt'), text = document.createElement('dd'), field = document.createElement('div'); label.textContent = name; text.textContent = value || 'Falta completar'; field.append(label, text); el('summary').append(field);
    }
    const state = user.registro_ad?.estado;
    const terminal = state && !['requiere_correccion', 'corregido'].includes(state);
    el('yes').disabled = Boolean(terminal); el('no').disabled = Boolean(terminal);
    el('status').textContent = terminal ? 'Estado: ' + state + '. Comprueba AD; no repitas el alta.' : 'Revisa los datos. Sí ejecutará todo el registro. La separación propuesta de nombres debe ser correcta.';
    const domain = draft().servicios_a_crear.includes('dominio');
    el('explanation').textContent = domain ? 'Al confirmar, el sistema registrará el usuario de Dominio y ejecutará la integración automatizada de Empleado y accesos en SGD.' : 'Al confirmar, el sistema ejecutará la integración automatizada de Empleado y accesos en SGD.';
    el('yes').hidden = false;
    el('status').hidden = false;
    el('no').hidden = !['requiere_correccion', 'corregido'].includes(state);
    el('no').textContent = 'Ajustar acceso manual';
    review.querySelector('h2').textContent = 'Revisa los datos antes del registro unificado';
    el('explanation').textContent = domain ? 'Comprueba los datos antes de confirmar el registro en Dominio y en SGD.' : 'Comprueba los datos antes de confirmar la integración con SGD.';
    view('review');
    validateSgd(user);
  }
  async function corrections() {
    if (busy || pending || !draft().servicios_a_crear.includes('dominio') || !['requiere_correccion', 'corregido'].includes(current().registro_ad?.estado)) return;
    const localVersion = version, person = el('person').value, d = draft();
    el('correction-scope').textContent = 'Ajusta el usuario, grupo o unidad organizativa que requiere la validación. Si el usuario ya existe, puedes añadir una letra del otro apellido. Para cambiar el DNI o los datos personales, vuelve a la entrada.';
    el('correction-person').textContent = `${d.given_names} ${d.paternal} ${d.maternal} · DNI ${d.dni}`;
    el('status').hidden = true;
    view('edit');
    el('user').value = d.username;
    el('yes').disabled = true;
    try {
      catalog = catalog || await api('catalogo'); if (localVersion !== version || person !== el('person').value || busy || document.body.dataset.adView !== 'edit') return;
      for (const [id, key, field] of [['group', 'grupos', 'group_dn'], ['ou', 'unidades_organizativas', 'ou_dn']]) {
        el(id).replaceChildren(new Option('Resolver automáticamente', ''));
        catalog[key].forEach(item => el(id).add(new Option(`${item.nombre}${item.cuenta ? ' — ' + item.cuenta : ''} · ${item.dn}`, item.dn))); el(id).value = d[field];
      }
    } catch (error) { el('status').textContent = error.message; showToast(error.message, 'error'); }
  }
  el('no').onclick = () => corrections(); el('person').onchange = show;
  el('corrections').onsubmit = event => {
    event.preventDefault();
    if (!['requiere_correccion', 'corregido'].includes(current().registro_ad?.estado)) return;
    Object.assign(draft(), {username: el('user').value.trim(), group_dn: el('group').value, ou_dn: el('ou').value});
    current().registro_ad = {estado: 'corregido'};
    publish(); show();
  };
  el('yes').onclick = async () => {
    if (busy || pending) return; const d = draft(), user = current();
    if (!d.paternal || !d.given_names || !d.area) { view('entry'); showToast('Completa los datos de la persona en la entrada antes de registrar.', 'error'); return; }
    lock(true); clearCredentials(); el('corrections').hidden = true; renderProgress({events: [], done: false});
    el('status').hidden = false;
    view('progress');
    user.registro_ad = {estado: 'en_proceso', datos_confirmados: {...d}}; publish(); el('status').textContent = 'Información confirmada. Iniciando registro automático…';
    try { const job = await api('automatico', {...d, servicios_a_crear: d.servicios_a_crear, reviewed: true}); pending = {id: job.job_id, user}; await follow(); }
    catch (error) {
      const rejected = error.status === 422;
      
      if (error.message.includes('empleado en SGD')) {
         Swal.fire({
            title: 'Empleado ya existe en SGD',
            text: 'El DNI ya está registrado como empleado en el SGD. ¿Deseas continuar creando únicamente su cuenta de Dominio?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, crear solo Dominio',
            cancelButtonText: 'Cancelar'
         }).then(async (result) => {
             if (result.isConfirmed) {
                 const d = draft();
                 d.servicios_a_crear = d.servicios_a_crear.filter(s => s !== 'sgd');
                 lock(false);
                 el('yes').disabled = false;
                 el('yes').click();
             } else {
                 user.registro_ad.estado = 'requiere_correccion'; publish(); lock(false);
                 el('yes').disabled = true; el('no').disabled = false;
                 await corrections();
                 el('status').hidden = true;
             }
         });
         return;
      }
      
      user.registro_ad.estado = rejected ? 'requiere_correccion' : 'resultado_incierto'; publish(); lock(false);
      el('yes').disabled = true; el('no').disabled = !rejected;
      if (rejected) await corrections();
      el('status').hidden = true;
      Swal.fire({
         title: rejected ? 'Revisa los datos' : 'Fallo en el registro',
         text: error.message + (rejected ? ' Corrige los datos antes de continuar.' : ' Comprueba AD antes de repetir el alta.'),
         icon: rejected ? 'warning' : 'error'
      });
    }
  };
  async function follow() {
    el('resume').hidden = true; el('resume').disabled = true;
    try {
      for (;;) {
        const state = await api('progreso/' + pending.id);
        renderProgress(state);
        if (state.done) {
          const {password, ...outcome} = state.result;
          const user = pending.user;
          user.registro_ad.estado = outcome.estado; user.registro_ad.resultado = outcome;
          pending = null; publish(); lock(false);
          const correctable = outcome.estado === 'requiere_correccion' && outcome.codigo_ldap !== 'InsufficientAccessRights';
          el('yes').disabled = true; el('no').disabled = !correctable;
          if (outcome.ok) {
            const domain = user.registro_ad.datos_confirmados.servicios_a_crear.includes('dominio');
            const sgd = user.registro_ad.datos_confirmados.servicios_a_crear.includes('sgd');
            const successDiv = el('credentials').querySelector('.registration-success');
            const eyebrow = successDiv.querySelector('.eyebrow');
            const title = successDiv.querySelector('h2');
            const desc = successDiv.querySelector('p');
            
            if (domain && sgd) {
                eyebrow.textContent = 'REGISTRO EXITOSO · DOMINIO Y SGD';
                title.textContent = 'Acceso a Dominio y SGD registrado correctamente';
                desc.textContent = 'La creación de la cuenta ha finalizado en ambos sistemas. A continuación se muestran las credenciales.';
            } else if (sgd) {
                eyebrow.textContent = 'REGISTRO EXITOSO · SGD';
                title.textContent = 'Usuario de SGD registrado correctamente';
                desc.textContent = 'La creación de la cuenta ha finalizado en SGD. A continuación se muestran las credenciales.';
            } else {
                eyebrow.textContent = 'REGISTRO EXITOSO · DOMINIO';
                title.textContent = 'Usuario de Dominio registrado correctamente';
                desc.textContent = 'La creación de la cuenta ha finalizado en el Dominio. Estas son sus credenciales de acceso.';
            }
            
            if (domain) {
                el('created-user').value = outcome.usuario; 
                el('created-password').value = password || '';
                el('created-user').parentElement.hidden = false;
                el('created-password').parentElement.hidden = false;
                el('secret-fields').querySelector('h3').hidden = false;
            } else {
                el('created-user').parentElement.hidden = true;
                el('created-password').parentElement.hidden = true;
                el('secret-fields').querySelector('h3').hidden = true;
            }
            if (sgd) {
                document.getElementById('sgd-secret-fields').hidden = false;
                document.getElementById('sgd-created-user').value = outcome.usuario;
                document.getElementById('sgd-created-password').value = user.registro_ad.datos_confirmados.dni;
            } else {
                document.getElementById('sgd-secret-fields').hidden = true;
            }
            
            try {
                const history = JSON.parse(localStorage.getItem('ad_registration_history') || '[]');
                history.unshift({
                    date: new Date().toLocaleString(),
                    name: (user.registro_ad.datos_confirmados.given_names + ' ' + user.registro_ad.datos_confirmados.paternal + ' ' + (user.registro_ad.datos_confirmados.maternal || '')).trim(),
                    dni: user.registro_ad.datos_confirmados.dni,
                    area: user.registro_ad.datos_confirmados.area,
                    domain: domain ? { user: outcome.usuario, pass: password || '' } : null,
                    sgd: sgd ? { user: outcome.usuario, pass: user.registro_ad.datos_confirmados.dni } : null
                });
                if(history.length > 50) history.pop();
                localStorage.setItem('ad_registration_history', JSON.stringify(history));
                if (window.renderHistory) window.renderHistory();
            } catch(e) { console.error('Error saving history', e); }
            el('secret-fields').hidden = false; el('hidden-notice').hidden = true; el('clear').hidden = false;
            el('status').hidden = true; view('credentials');
          }
          else {
            const isSgdDuplicate = outcome.mensaje && outcome.mensaje.includes('empleado en SGD');
            el('corrections').hidden = true;
            if (correctable && !isSgdDuplicate) await corrections();
            el('status').hidden = true;
            
            if (isSgdDuplicate) {
               const d = draft();
               if (d.servicios_a_crear.includes('dominio')) {
                   Swal.fire({
                      title: 'Empleado ya existe en SGD',
                      text: 'El DNI ya está registrado como empleado en el SGD. ¿Deseas continuar creando únicamente su cuenta de Dominio?',
                      icon: 'question',
                      showCancelButton: true,
                      confirmButtonColor: '#3085d6',
                      cancelButtonColor: '#d33',
                      confirmButtonText: 'Sí, registrar solo dominio',
                      cancelButtonText: 'Volver a verificar DNI / Datos'
                   }).then(async (result) => {
                       if (result.isConfirmed) {
                           d.servicios_a_crear = d.servicios_a_crear.filter(s => s !== 'sgd');
                           lock(false);
                           el('yes').disabled = false;
                           el('yes').click();
                       } else {
                           user.registro_ad.estado = 'resultado_incierto'; publish(); lock(false);
                           el('yes').disabled = true; el('no').disabled = false;
                           view('entry');
                       }
                   });
               } else {
                   Swal.fire({
                      title: 'Empleado ya existe en SGD',
                      text: 'El DNI ya está registrado como empleado en el SGD. No se pueden crear duplicados.',
                      icon: 'error',
                      confirmButtonText: 'Volver a verificar DNI / Datos'
                   }).then(() => {
                       user.registro_ad.estado = 'resultado_incierto'; publish(); lock(false);
                       el('yes').disabled = true; el('no').disabled = false;
                       view('entry');
                   });
               }
            } else {
               const errText = outcome.codigo_ldap === 'InsufficientAccessRights'
                 ? 'Permisos insuficientes. La cuenta que ejecuta la aplicación no está autorizada para completar esta operación. No necesitas corregir los datos de la persona; revisa los permisos con el administrador.'
                 : correctable ? outcome.mensaje : 'No se pudo completar el registro. Consulta el detalle de las operaciones y comprueba el estado en Active Directory antes de reintentarlo.';
                 
               Swal.fire({
                  title: 'Error durante el registro',
                  text: errText,
                  icon: 'error'
               });
               
               if (!correctable) el('back').hidden = false;
            }
          }
          break;
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    } catch (error) { el('status').textContent = 'El seguimiento se interrumpió; el registro puede continuar. Pulsa Retomar seguimiento. ' + error.message; el('resume').hidden = false; el('resume').disabled = false; }
  }
  el('resume').onclick = follow;
  el('clear').onclick = () => {
    el('created-password').value = ''; el('created-user').value = '';
    el('secret-fields').hidden = true; el('hidden-notice').hidden = false; el('clear').hidden = true;
  };
  el('back').onclick = () => { if (!busy && !pending) { clearCredentials(); view('entry'); } };
  el('another').onclick = () => { if (!busy && !pending) { clearCredentials(); view('entry'); } };
  window.startAdRegistration = result => {
    if (busy) return; version++; source = result; catalog = null; clearCredentials();
    indices = result.usuarios.map((_, i) => i).filter(i => !result.usuarios[i].servicios_a_crear || result.usuarios[i].servicios_a_crear.includes('dominio') || result.usuarios[i].servicios_a_crear.includes('sgd'));
    drafts = indices.map(index => {
      const user = result.usuarios[index], original = user.nombre_completo_original.trim().split(/\s+/), inferred = !user.apellidos && !user.nombres && original.length >= 3;
      const last = (inferred ? original.slice(0, 2) : (user.apellidos || '').split(/\s+/)).filter(Boolean);
      return {paternal: last.length <= 2 ? last[0] || '' : '', maternal: last.length === 2 ? last[1] : '', given_names: user.nombres || (inferred ? original.slice(2).join(' ') : ''), area: user.area || '', username: '', group_dn: '', ou_dn: '', dni: user.dni || '', servicios_a_crear: user.servicios_a_crear || ['dominio']};
    });
    indices.forEach((index, i) => { source.usuarios[index].datos_sgd = {...drafts[i]}; });
    el('person').replaceChildren(); indices.forEach((index, i) => el('person').add(new Option(result.usuarios[index].nombre_completo_original, i)));
    el('person').hidden = indices.length === 1; section.querySelector('label[for="ad-person"]').hidden = indices.length === 1;
    section.hidden = !indices.length; if (indices.length) show(); else view('entry');
  };
  window.hideAdRegistration = () => { if (!busy) { version++; clearCredentials(); view('entry'); } };
})();
