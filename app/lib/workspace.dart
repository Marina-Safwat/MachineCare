import 'package:flutter/material.dart';
import 'api.dart';

String cleanError(Object e) => e.toString().replaceFirst('Exception: ', '');
String date(dynamic value) => value == null ? 'Not recorded' : value.toString().split('T').first;
List<Map<String, dynamic>> rows(Map<String, dynamic> s, String key) => (s[key] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
Future<bool> changePassword(BuildContext context, Api api) async {
  final old = TextEditingController(), next = TextEditingController();
  final result = await showDialog<bool>(context: context, barrierDismissible: false, builder: (context) => EntryDialog(title: 'Change password', fields: [EntryField('current_password', 'Current password', old, secret: true), EntryField('new_password', 'New password (12+ characters)', next, secret: true)], onSave: (d) async { await api.action('password', d); }));
  return result == true;
}
class EntryField {
  final String key, label; final TextEditingController controller; final bool number, decimal, secret, optional;
  EntryField(this.key, this.label, this.controller, {this.number = false, this.decimal = false, this.secret = false, this.optional = false});
}
class EntryDialog extends StatefulWidget {
  final String title; final List<EntryField> fields; final Future<void> Function(Map<String, dynamic>) onSave;
  final Widget? intro;
  const EntryDialog({super.key, required this.title, required this.fields, required this.onSave, this.intro});
  @override State<EntryDialog> createState() => _EntryDialogState();
}
class _EntryDialogState extends State<EntryDialog> {
  // EntryDialog owns these controllers until its route has fully unmounted.
  @override
  void dispose() {
    for (final controller in widget.fields.map((f) => f.controller).toSet()) {
      controller.dispose();
    }
    super.dispose();
  }
  bool busy = false; String? error;
  Future<void> save() async {
    setState(() { busy = true; error = null; });
    try {
      final d = <String, dynamic>{};
      for (final f in widget.fields) {
        final v = f.controller.text;
        if (!f.optional && v.trim().isEmpty) throw Exception('${f.label} is required.');
        d[f.key] = f.number ? int.parse(v) : f.decimal ? double.parse(v) : v;
      }
      await widget.onSave(d);
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => AlertDialog(title: Text(widget.title), content: SizedBox(width: 480, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
    if (widget.intro != null) widget.intro!,
    for (final f in widget.fields) Padding(padding: const EdgeInsets.only(top: 14), child: TextField(controller: f.controller, obscureText: f.secret, enabled: !busy, keyboardType: f.number || f.decimal ? TextInputType.number : TextInputType.text, decoration: InputDecoration(labelText: f.label))),
    if (error != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(error!, style: const TextStyle(color: Colors.red))),
  ]))), actions: [TextButton(onPressed: busy ? null : () => Navigator.pop(context, false), child: const Text('Cancel')), FilledButton(onPressed: busy ? null : save, child: Text(busy ? 'Saving…' : 'Save'))]);
}
class Workspace extends StatefulWidget {
  final Api api;
  const Workspace({super.key, required this.api});
  @override State<Workspace> createState() => _WorkspaceState();
}
class _WorkspaceState extends State<Workspace> {
  Map<String, dynamic> state = {}; bool loading = true; String? error; int page = 0; String search = '';
  int? filterBuilding, filterLine, filterType;
  String? filterStation, filterStatus;
  final equipmentSearch = TextEditingController();
  @override void dispose() { equipmentSearch.dispose(); super.dispose(); }
  static const pages = ['Overview', 'Equipment', 'Inventory', 'Approvals', 'History', 'Administration', 'Notifications'];
  static const icons = [Icons.dashboard_outlined, Icons.precision_manufacturing_outlined, Icons.inventory_2_outlined, Icons.fact_check_outlined, Icons.history, Icons.settings_outlined, Icons.notifications_outlined];
  bool get admin => state['user']?['role'] == 'Administrator';
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async {
    if (mounted) setState(() { loading = true; error = null; });
    try { final s = await widget.api.call('/state'); if (mounted) setState(() => state = s); }
    catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => loading = false); }
  }
  Future<void> act(String name, Map<String, dynamic> d) async {
    try { await widget.api.action(name, d); await refresh(); }
    catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(cleanError(e)))); }
  }
  Future<void> form(String title, String action, List<List<String>> specs, {Map<String, dynamic> extra = const {}, String? intro}) async {
    final fields = specs.map((s) => EntryField(s[0], s[1], TextEditingController(text: s.length > 3 ? s[3] : ''), number: s.length > 2 && s[2] == 'int', decimal: s.length > 2 && s[2] == 'decimal', secret: s[0].contains('password'), optional: s.length > 2 && s[2] == 'optional')).toList();
    await showDialog<bool>(context: context, builder: (_) => EntryDialog(title: title, fields: fields, intro: intro == null ? null : Text(intro), onSave: (d) async { if (action == 'part') { d['type_ids'] = (d['type_ids'] as String).split(',').map((v) => int.parse(v.trim())).toList(); } await widget.api.action(action, {...extra, ...d}); }));
    if (!mounted) return;
    await refresh();
  }
  Widget panel(String title, List<Widget> children, {Widget? trailing}) => Card(child: Padding(padding: const EdgeInsets.all(22), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Expanded(child: Text(title, style: Theme.of(context).textTheme.titleLarge)), if (trailing != null) trailing]), const SizedBox(height: 14), ...children])));
  Widget pill(String text) => Chip(label: Text(text), visualDensity: VisualDensity.compact);
  Widget overview() {
    final machines = rows(state, 'machines'), parts = rows(state, 'parts'), requests = rows(state, 'requests'), history = rows(state, 'history');
    final low = parts.where((p) => p['stock'] <= p['threshold']).toList();
    final pending = requests.where((r) => r['state'] == 'Pending').length;
    final spend = history.fold<double>(0, (sum, h) => sum + (h['quantity'] as num) * (h['unit_cost'] as num));
    int overdue = 0;
    for (final m in machines) { for (final p in (m['parts'] as List)) { if (p['last_replacement'] != null && DateTime.now().difference(DateTime.parse(p['last_replacement'] as String)).inDays >= (p['interval_days'] as int)) overdue++; } }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Keep production moving.', style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700)), const SizedBox(height: 8), const Text('One place for equipment, replacement decisions, and shared spare parts.'), const SizedBox(height: 22),
      Wrap(spacing: 12, runSpacing: 12, children: [metric('Machines', '${machines.length}', Icons.precision_manufacturing), metric('Low-stock SKUs', '${low.length}', Icons.inventory), metric('Pending approvals', '$pending', Icons.approval), metric('Recorded spending', '\$${spend.toStringAsFixed(2)}', Icons.payments)]),
      const SizedBox(height: 18), panel('Production status', [Wrap(spacing: 12, children: ['Operating', 'Maintenance', 'Stopped', 'Retired'].map((s) => pill('$s: ${machines.where((m) => m['status'] == s).length}')).toList()), Text('$overdue machine/part intervals overdue. No history means due date unknown.')]),
      panel('Stock needs attention', low.isEmpty ? [const Text('No low-stock parts.')] : low.map((p) => ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.warning_amber, color: Colors.orange), title: Text(p['name'] as String), subtitle: Text('${p['sku']} • ${p['bin']}'), trailing: Text('${p['stock']} available / ${p['threshold']} threshold'))).toList()),
      panel('Recent replacements', history.take(5).map((h) => ListTile(contentPadding: EdgeInsets.zero, title: Text('${h['part']} • ${h['location_snapshot']}'), subtitle: Text('${date(h['replaced'])} • ${h['technician']} • Qty ${h['quantity']}'))).toList().isEmpty ? [const Text('No completed replacements yet.')] : history.take(5).map((h) => ListTile(contentPadding: EdgeInsets.zero, title: Text('${h['part']} • ${h['location_snapshot']}'), subtitle: Text('${date(h['replaced'])} • ${h['technician']} • Qty ${h['quantity']}'))).toList()),
      const Padding(padding: EdgeInsets.all(12), child: Text('Pilot: in-app notifications available. Automatic email and purchasing are not connected.')),
    ]);
  }
  Widget metric(String label, String value, IconData icon) => SizedBox(width: 230, child: Card(child: Padding(padding: const EdgeInsets.all(22), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(icon, color: const Color(0xff0c756c)), const SizedBox(height: 18), Text(value, style: const TextStyle(fontSize: 30, fontWeight: FontWeight.bold)), Text(label)]))));
  Widget equipmentFilter(String label, String? value, Map<String, String> options, void Function(String?) changed) => SizedBox(
    width: 210,
    child: DropdownButtonFormField<String>(
      key: ValueKey('$label:$value:${options.keys.join(",")}'),
      value: options.containsKey(value) ? value : null,
      isExpanded: true,
      hint: const Text('All'),
      decoration: InputDecoration(labelText: label),
      items: [const DropdownMenuItem<String>(value: null, child: Text('All')), ...options.entries.map((e) => DropdownMenuItem<String>(value: e.key, child: Text(e.value, overflow: TextOverflow.ellipsis)))],
      onChanged: changed,
    ),
  );
  Widget equipment() {
    final all = rows(state, 'machines');
    final buildings = rows(state, 'buildings');
    final lines = rows(state, 'lines').where((l) => filterBuilding == null || l['building_id'] == filterBuilding).toList();
    final types = rows(state, 'types');
    final stations = all.where((m) => (filterBuilding == null || m['building_id'] == filterBuilding) && (filterLine == null || m['line_id'] == filterLine) && (filterType == null || m['type_id'] == filterType)).map((m) => m['station'].toString()).toSet().toList()..sort();
    final ms = all.where((m) =>
      (filterBuilding == null || m['building_id'] == filterBuilding) &&
      (filterLine == null || m['line_id'] == filterLine) &&
      (filterType == null || m['type_id'] == filterType) &&
      (filterStation == null || m['station'].toString() == filterStation) &&
      (filterStatus == null || m['status'] == filterStatus) &&
      '${m['name']} ${m['asset_tag']} ${m['serial']} ${m['status']}'.toLowerCase().contains(search.trim().toLowerCase())
    ).toList();
    final active = search.trim().isNotEmpty || filterBuilding != null || filterLine != null || filterType != null || filterStation != null || filterStatus != null;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      panel('Find equipment', [
        TextField(controller: equipmentSearch, decoration: const InputDecoration(labelText: 'Search machine, asset tag or serial number', prefixIcon: Icon(Icons.search)), onChanged: (s) => setState(() => search = s)),
        const SizedBox(height: 16),
        Wrap(spacing: 12, runSpacing: 16, children: [
          equipmentFilter('Building', filterBuilding?.toString(), {for (final b in buildings) '${b['id']}': '${b['code']} · ${b['name']}'}, (v) => setState(() { filterBuilding = v == null ? null : int.parse(v); filterLine = null; filterStation = null; })),
          equipmentFilter('Production line', filterLine?.toString(), {for (final l in lines) '${l['id']}': '${buildings.where((b) => b['id'] == l['building_id']).map((b) => b['code']).join()} · ${l['code']}'}, (v) => setState(() { filterLine = v == null ? null : int.parse(v); filterStation = null; })),
          equipmentFilter('Machine type', filterType?.toString(), {for (final t in types) '${t['id']}': t['name'] as String}, (v) => setState(() { filterType = v == null ? null : int.parse(v); filterStation = null; })),
          equipmentFilter('Station / position', filterStation, {for (final station in stations) station: 'Station $station'}, (v) => setState(() => filterStation = v)),
          equipmentFilter('Operating status', filterStatus, {for (final status in ['Operating', 'Maintenance', 'Stopped', 'Retired']) status: status}, (v) => setState(() => filterStatus = v)),
        ]),
        const SizedBox(height: 16),
        Wrap(spacing: 16, crossAxisAlignment: WrapCrossAlignment.center, children: [
          Text('${ms.length} of ${all.length} accessible machines', style: const TextStyle(fontWeight: FontWeight.w600)),
          TextButton.icon(onPressed: active ? () => setState(() { filterBuilding = null; filterLine = null; filterType = null; filterStation = null; filterStatus = null; search = ''; equipmentSearch.clear(); }) : null, icon: const Icon(Icons.filter_alt_off_outlined), label: const Text('Clear filters')),
        ]),
      ]),
      if (ms.isEmpty) const Padding(padding: EdgeInsets.all(28), child: Text('No machines match these filters. Clear filters or choose another location.', textAlign: TextAlign.center)),
      for (final b in buildings.where((b) => ms.any((m) => m['building_id'] == b['id']))) Card(child: ExpansionTile(key: ValueKey('building:${b['id']}:$active'), title: Text('${b['code']} · ${b['name']}'), initiallyExpanded: true, children: [
        for (final l in lines.where((l) => l['building_id'] == b['id'] && ms.any((m) => m['line_id'] == l['id']))) ExpansionTile(key: ValueKey('line:${l['id']}:$active'), title: Text(l['code'] as String), initiallyExpanded: active, children: [
          for (final t in types.where((t) => ms.any((m) => m['line_id'] == l['id'] && m['type_id'] == t['id']))) ExpansionTile(title: Text(t['name'] as String), initiallyExpanded: true, children: [
            for (final m in ms.where((m) => m['line_id'] == l['id'] && m['type_id'] == t['id'])) ListTile(title: Text(m['name'] as String), subtitle: Text('Asset ${m['asset_tag']}'), trailing: pill(m['status'] as String), onTap: () => machineDetails(m)),
          ]),
        ]),
      ])),
    ]);
  }
  Future<void> machineDetails(Map<String, dynamic> m) async {
    final route = DialogRoute<Map<String, dynamic>>(context: context, builder: (ctx) => AlertDialog(title: Text(m['name'] as String), content: SizedBox(width: 680, child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Asset: ${m['asset_tag']} • Serial: ${m['serial']} • ${m['status']}'), const SizedBox(height: 18), const Text('Compatible parts • shared inventory', style: TextStyle(fontWeight: FontWeight.bold)),
      for (final p in (m['parts'] as List)) Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${p['name']} · ${p['sku']}', style: const TextStyle(fontWeight: FontWeight.bold)), Text('Last replacement: ${date(p['last_replacement'])}'), Text('${p['stock']} available • ${p['bin']} • expected ${p['interval_days']} days'), Align(alignment: Alignment.centerRight, child: FilledButton.tonal(onPressed: m['status'] == 'Retired' ? null : () => Navigator.pop(ctx, Map<String, dynamic>.from(p as Map)), child: const Text('Replace this part')))]))),
      const SizedBox(height: 18), const Text('Requests', style: TextStyle(fontWeight: FontWeight.bold)),
      for (final r in rows(state, 'requests').where((r) => r['machine_id'] == m['id'])) Text('#${r['id']} ${r['part']} • ${r['state']}'),
      const SizedBox(height: 18), const Text('Maintenance history', style: TextStyle(fontWeight: FontWeight.bold)),
      for (final h in rows(state, 'history').where((h) => h['machine_id'] == m['id'])) Text('${date(h['replaced'])} • ${h['part']} • ${h['technician']}'),
    ]))), actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close'))]));
    final selectedPart = await Navigator.of(context).push(route);
    await route.completed;
    if (!mounted || selectedPart == null) return;
    await request(m, selectedPart);
  }
  Future<void> request(Map<String, dynamic> m, Map<String, dynamic> p) async {
    final last = p['last_replacement'];
    final elapsed = last == null ? null : DateTime.now().toUtc().difference(DateTime.parse(last as String)).inDays;
    final early = elapsed != null && elapsed < (p['interval_days'] as int);
    await form(early ? 'Early replacement • lead approval required' : 'Request replacement', 'request', [ ['quantity', 'Quantity', 'int', '1'], ['reason', 'Reason'], ['notes', 'Notes', 'optional'], if (early) ['early_explanation', 'Required early replacement explanation'] ], extra: {'machine_id': m['id'], 'part_id': p['id'], 'operation_key': 'request:${DateTime.now().microsecondsSinceEpoch}:${state['user']['id']}'}, intro: '${m['name']}\n${p['name']} • ${p['stock']} available at ${p['bin']}\nPrevious: ${date(last)} • expected ${p['interval_days']} days\n${early ? 'WARNING: only $elapsed days elapsed. Assigned lead must approve.' : 'No early replacement detected.'}\nSubmitting does not deduct inventory. Record completion after physical work.');
  }
  Widget inventory() => Column(children: [
    if (admin) Align(alignment: Alignment.centerRight, child: FilledButton.icon(onPressed: addPart, icon: const Icon(Icons.add), label: const Text('Add part'))),
    for (final p in rows(state, 'parts')) panel('${p['name']} · ${p['sku']}', [Text('Shared stock: ${p['stock']} • Bin: ${p['bin']}'), Text('Threshold ${p['threshold']} • Target ${p['target']} • Expected life ${p['interval_days']} days'), Text('Unit cost \$${(p['cost'] as num).toStringAsFixed(2)} • Supplier: ${p['supplier']}'), if (p['stock'] <= p['threshold']) const Text('LOW STOCK • reorder planning required', style: TextStyle(color: Colors.deepOrange)), if (admin) Wrap(spacing: 10, children: [TextButton.icon(onPressed: () => editPart(p), icon: const Icon(Icons.edit_outlined), label: const Text('Edit details')), TextButton(onPressed: () => form('Receive stock', 'receipt', [['quantity', 'Received quantity', 'int'], ['reason', 'Receipt reference / reason']], extra: {'part_id': p['id'], 'operation_key': 'receipt:${DateTime.now().microsecondsSinceEpoch}'}), child: const Text('Receive')), TextButton(onPressed: () => form('Adjust inventory', 'adjust', [['delta', 'Signed adjustment (+ / −)', 'int'], ['reason', 'Required adjustment reason']], extra: {'part_id': p['id'], 'operation_key': 'adjust:${DateTime.now().microsecondsSinceEpoch}'}), child: const Text('Adjust'))])]),
  ]);
  Future<void> addPart() => editPart(null);
  Future<void> editPart(Map<String, dynamic>? part) async {
    final types = rows(state, 'types');
    if (types.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Create a machine type before adding parts.')));
      return;
    }
    await showDialog<bool>(context: context, builder: (_) => PartEditor(
      part: part, types: types,
      onSave: (data) async { await widget.api.action(part == null ? 'part' : 'edit_part', data); },
    ));
    if (!mounted) return;
    await refresh();
  }
  Widget approvals() => Column(children: [if (rows(state, 'requests').isEmpty) const Text('No replacement requests.'), for (final r in rows(state, 'requests')) panel('#${r['id']} · ${r['part']}', [Wrap(spacing: 8, children: [pill(r['state'] as String), if (r['early'] == 1) pill('Early replacement')]), Text('Machine #${r['machine_id']} • Qty ${r['quantity']} • ${r['technician']}'), Text(r['reason'] as String), Text(r['notes'] as String), if (r['review_comment'] != null) Text('Lead comment: ${r['review_comment']}'), Wrap(spacing: 10, children: [if (r['state'] == 'Pending' && r['lead_id'] == state['user']['id']) ...[FilledButton(onPressed: () => review(r, 'Approved'), child: const Text('Approve')), OutlinedButton(onPressed: () => review(r, 'Rejected'), child: const Text('Reject'))], if (r['state'] == 'Approved' && r['technician_id'] == state['user']['id']) FilledButton(onPressed: () => confirmComplete(r), child: const Text('Record physical completion')), if (['Pending', 'Approved'].contains(r['state']) && (admin || r['technician_id'] == state['user']['id'])) TextButton(onPressed: () => act('cancel', {'request_id': r['id']}), child: const Text('Cancel request'))])])]);
  Future<void> review(Map<String, dynamic> r, String decision) => form('$decision request #${r['id']}', 'review', [['comment', 'Lead review comment']], extra: {'request_id': r['id'], 'decision': decision});
  Future<void> confirmComplete(Map<String, dynamic> r) async {
    final yes = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: const Text('Confirm physical replacement'), content: Text('Has quantity ${r['quantity']} of ${r['part']} actually been replaced? This records maintenance and deducts shared stock.'), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Back')), FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Yes, record completion'))]));
    if (yes == true) await act('complete', {'request_id': r['id']});
  }
  Widget history() => Column(children: [const Text('Completed work only • historical location and cost preserved'), if (rows(state, 'history').isEmpty) const Padding(padding: EdgeInsets.all(24), child: Text('No completed maintenance recorded.')), for (final h in rows(state, 'history')) panel(h['part'] as String, [Text(h['location_snapshot'] as String), Text('${date(h['replaced'])} • ${h['technician']} • Qty ${h['quantity']}'), Text('Recorded cost: \$${((h['quantity'] as num) * (h['unit_cost'] as num)).toStringAsFixed(2)}'), Text(h['reason'] as String)])]);
  Widget administration() {
    if (!admin) return const Text('Administrator permission required.');
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      panel('Buildings & lines', [Wrap(spacing: 12, children: [FilledButton.tonal(onPressed: () => form('Create building', 'building', [['code', 'Building code'], ['name', 'Building name']]), child: const Text('Add building')), FilledButton.tonal(onPressed: () => form('Create line', 'line', [['building_id', 'Building ID', 'int'], ['code', 'Line code'], ['description', 'Description (optional)', 'optional']]), child: const Text('Add line'))]), for (final b in rows(state, 'buildings')) ListTile(title: Text('#${b['id']} ${b['code']} · ${b['name']}'), trailing: IconButton(tooltip: 'Edit building', icon: const Icon(Icons.edit_outlined), onPressed: () => form('Edit building', 'building', [['code', 'Code', 'text', b['code'] as String], ['name', 'Name', 'text', b['name'] as String]], extra: {'id': b['id']}))), for (final l in rows(state, 'lines')) ListTile(title: Text('Line #${l['id']} • Building ${l['building_id']} • ${l['code']}'), subtitle: Text(l['description'] as String), trailing: IconButton(tooltip: 'Edit line', icon: const Icon(Icons.edit_outlined), onPressed: () => form('Edit line', 'line', [['building_id', 'Building ID', 'int', '${l['building_id']}'], ['code', 'Code', 'text', l['code'] as String], ['description', 'Description (optional)', 'optional', l['description'] as String]], extra: {'id': l['id']})))]),
      panel('Machine types', [FilledButton.tonal(onPressed: () => form('Add machine type', 'type', [['name', 'Machine type name']]), child: const Text('Add type')), for (final t in rows(state, 'types')) ListTile(title: Text(t['name'] as String), subtitle: Text('Type ID ${t['id']}'), trailing: IconButton(tooltip: 'Rename machine type', icon: const Icon(Icons.edit_outlined), onPressed: () => form('Rename machine type', 'type', [['name', 'Machine type name', 'text', t['name'] as String]], extra: {'id': t['id'], 'revision': t['revision'] ?? 0}, intro: 'Machine assignments and compatible parts keep their existing links. Recorded maintenance locations keep their original names.'))) ]),
      panel('Equipment registry', [FilledButton.tonal(onPressed: () => editMachine(null), child: const Text('Register machine')), for (final m in rows(state, 'machines')) ListTile(title: Text(m['name'] as String), subtitle: Text('Machine ID ${m['id']}'), trailing: IconButton(tooltip: 'Edit, move or retire machine', icon: const Icon(Icons.edit_outlined), onPressed: () => editMachine(m)))]),
      panel('Accounts', [FilledButton.tonal(onPressed: createUser, child: const Text('Create employee account')), for (final u in rows(state, 'users')) ListTile(title: Text('${u['username']} · ${u['role']}'), subtitle: Text('ID ${u['id']} • Lead ${u['lead_id'] ?? 'unassigned'} • ${u['active'] == 1 ? 'Active' : 'Disabled'}'), trailing: u['id'] == state['user']['id'] ? null : Wrap(children: [IconButton(tooltip: 'Edit role, lead, building and line access', icon: const Icon(Icons.edit_outlined), onPressed: () => editUser(u)), IconButton(tooltip: 'Reset password', icon: const Icon(Icons.key), onPressed: () => form('Reset employee password', 'reset', [['password', 'Temporary password (12+ characters)']], extra: {'user_id': u['id']})), IconButton(tooltip: u['active'] == 1 ? 'Disable' : 'Enable', icon: Icon(u['active'] == 1 ? Icons.block : Icons.check_circle_outline), onPressed: () => act('disable', {'user_id': u['id'], 'active': u['active'] == 1 ? 0 : 1}))]))]),
    ]);
  }
  Future<void> editMachine(Map<String, dynamic>? m) => form(m == null ? 'Register machine' : 'Edit / move / retire machine', 'machine', [['line_id', 'Line ID', 'int', '${m?['line_id'] ?? ''}'], ['type_id', 'Type ID', 'int', '${m?['type_id'] ?? ''}'], ['station', 'Station / position within line', 'text', '${m?['station'] ?? ''}'], ['asset_tag', 'Unique asset tag', 'text', '${m?['asset_tag'] ?? ''}'], ['serial', 'Serial number', 'optional', '${m?['serial'] ?? ''}'], ['status', 'Operating / Maintenance / Stopped / Retired', 'text', '${m?['status'] ?? 'Operating'}']], extra: {if (m != null) 'id': m['id']});
  Future<void> editUser(Map<String, dynamic> user) async {
    await showDialog<bool>(context: context, builder: (_) => AccountEditor(
      user: user,
      users: rows(state, 'users'),
      buildings: rows(state, 'buildings'),
      lines: rows(state, 'lines'),
      onSave: (data) async { await widget.api.action('edit_user', data); },
    ));
    if (!mounted) return;
    await refresh();
  }
  Future<void> createUser() async {
    await showDialog<bool>(context: context, builder: (_) => AccountEditor(
      creating: true,
      user: const {'role': 'Technician', 'building_ids': [], 'line_ids': []},
      users: rows(state, 'users'), buildings: rows(state, 'buildings'), lines: rows(state, 'lines'),
      onSave: (data) async { await widget.api.action('user', data); },
    ));
    if (!mounted) return;
    await refresh();
  }
  Widget notifications() => Column(children: [const Text('Automatic email unavailable in this pilot.'), if (rows(state, 'notifications').isEmpty) const Padding(padding: EdgeInsets.all(24), child: Text('No notifications.')), for (final n in rows(state, 'notifications')) Card(child: ListTile(leading: const Icon(Icons.notifications_outlined), title: Text(n['message'] as String), subtitle: Text(date(n['created']))))]);
  @override Widget build(BuildContext context) {
    final content = loading && state.isEmpty ? const Center(child: CircularProgressIndicator()) : error != null ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [Text(error!), TextButton(onPressed: refresh, child: const Text('Retry'))])) : SingleChildScrollView(padding: const EdgeInsets.all(28), child: [overview, equipment, inventory, approvals, history, administration, notifications][page]());
    final nav = ListView(children: [const Padding(padding: EdgeInsets.all(24), child: Text('MachineCare', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800))), for (var i = 0; i < pages.length; i++) if (i != 5 || admin) ListTile(selected: page == i, leading: Icon(icons[i]), title: Text(pages[i]), onTap: () { setState(() => page = i); if (MediaQuery.sizeOf(context).width < 900) Navigator.pop(context); }), const Divider(), const Padding(padding: EdgeInsets.all(20), child: Text('LOCAL PILOT\nSample equipment\nEmail not configured', style: TextStyle(fontSize: 12)))]);
    return LayoutBuilder(builder: (ctx, size) => Scaffold(appBar: AppBar(title: Text(pages[page]), actions: [Center(child: Text('${state['user']?['username'] ?? ''} • ${state['user']?['role'] ?? ''}')), IconButton(tooltip: 'Refresh', onPressed: loading ? null : refresh, icon: const Icon(Icons.refresh)), IconButton(tooltip: 'Change password', onPressed: () async { if (await changePassword(context, widget.api) && context.mounted) Navigator.pop(context); }, icon: const Icon(Icons.password)), IconButton(tooltip: 'Sign out', onPressed: () async { try { await widget.api.action('logout', {}); } finally { widget.api.token = null; if (context.mounted) Navigator.pop(context); } }, icon: const Icon(Icons.logout))]), drawer: size.maxWidth < 900 ? Drawer(child: nav) : null, body: Column(children: [if (loading) const LinearProgressIndicator(), Expanded(child: Row(children: [if (size.maxWidth >= 900) SizedBox(width: 235, child: Material(color: Colors.white, child: nav)), Expanded(child: content)]))])));
  }
}

/// Administrator editor: names stay stable while permissions can change.
class AccountEditor extends StatefulWidget {
  final Map<String, dynamic> user;
  final List<Map<String, dynamic>> users, buildings, lines;
  final bool creating;
  final Future<void> Function(Map<String, dynamic>) onSave;
  const AccountEditor({super.key, required this.user, required this.users, required this.buildings, this.lines = const [], this.creating = false, required this.onSave});
  @override State<AccountEditor> createState() => _AccountEditorState();
}
class _AccountEditorState extends State<AccountEditor> {
  late String role;
  int? leadId;
  late Set<int> buildingIds, lineIds;
  final username = TextEditingController(), password = TextEditingController();
  @override void dispose() { username.dispose(); password.dispose(); super.dispose(); }
  bool busy = false;
  String? error;
  @override void initState() {
    super.initState();
    role = widget.user['role'] as String;
    leadId = widget.user['lead_id'] as int?;
    buildingIds = (widget.user['building_ids'] as List? ?? []).cast<int>().toSet();
    lineIds = (widget.user['line_ids'] as List? ?? []).cast<int>().toSet();
  }
  Future<void> save() async {
    setState(() { busy = true; error = null; });
    try {
      if (widget.creating && username.text.trim().isEmpty) throw Exception('Username is required.');
      if (widget.creating && password.text.length < 12) throw Exception('Use a temporary password of at least 12 characters.');
      await widget.onSave({if (!widget.creating) 'user_id': widget.user['id'], if (widget.creating) ...{'username': username.text.trim(), 'password': password.text}, 'role': role, 'lead_id': role == 'Technician' ? leadId : null, 'building_ids': buildingIds.toList()..sort(), 'line_ids': lineIds.toList()..sort()});
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) {
    final leads = widget.users.where((u) => u['role'] == 'Lead' && u['active'] == 1 && u['id'] != widget.user['id']).toList();
    return AlertDialog(
      title: Text(widget.creating ? 'Create employee account' : 'Edit account · ${widget.user['username']}'),
      content: SizedBox(width: 520, child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        if (widget.creating) ...[
          TextField(controller: username, enabled: !busy, decoration: const InputDecoration(labelText: 'Username')),
          const SizedBox(height: 16),
          TextField(controller: password, enabled: !busy, obscureText: true, decoration: const InputDecoration(labelText: 'Temporary password (12+ characters)')),
          const SizedBox(height: 12),
          const Text('This employee must change the temporary password on first login.'),
        ] else
        const Text('Permission changes sign this employee out. Pending early requests move to the newly assigned lead; completed history stays intact.'),
        const SizedBox(height: 18),
        DropdownButtonFormField<String>(value: role, decoration: const InputDecoration(labelText: 'Role'), items: ['Administrator', 'Lead', 'Technician'].map((r) => DropdownMenuItem(value: r, child: Text(r))).toList(), onChanged: busy ? null : (r) => setState(() { role = r!; if (role != 'Technician') leadId = null; })),
        if (role == 'Technician') ...[
          const SizedBox(height: 16),
          DropdownButtonFormField<int>(key: ValueKey('lead:$leadId'), value: leads.any((u) => u['id'] == leadId) ? leadId : null, hint: const Text('Unassigned'), decoration: const InputDecoration(labelText: 'Assigned lead'), items: [const DropdownMenuItem<int>(value: null, child: Text('Unassigned')), ...leads.map((u) => DropdownMenuItem<int>(value: u['id'] as int, child: Text(u['username'] as String)))], onChanged: busy ? null : (v) => setState(() => leadId = v)),
          const SizedBox(height: 8),
          const Text('An unassigned technician cannot submit early replacements.'),
        ],
        const SizedBox(height: 20),
        const Text('Building and production-line access', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text('Grant a whole building, including future lines, or select individual lines. Selecting a line does not grant access to its siblings.'),
        if (role == 'Administrator') const Text('Administrators have access to all buildings and lines.'),
        for (final b in widget.buildings) ...[
          CheckboxListTile(contentPadding: EdgeInsets.zero, title: Text('${b['code']} · ${b['name']}'), subtitle: const Text('Whole building — all current and future lines'), value: role == 'Administrator' || buildingIds.contains(b['id']), onChanged: busy || role == 'Administrator' ? null : (selected) => setState(() { if (selected == true) { buildingIds.add(b['id'] as int); } else { buildingIds.remove(b['id']); } })),
          for (final line in widget.lines.where((l) => l['building_id'] == b['id'])) Padding(padding: const EdgeInsets.only(left: 24), child: CheckboxListTile(
            key: ValueKey('line-access:${line['id']}'), contentPadding: EdgeInsets.zero,
            title: Text('${b['code']} · ${line['code']}'),
            subtitle: Text(role == 'Administrator' || buildingIds.contains(b['id']) ? 'Included through whole-building access' : 'This production line only'),
            value: role == 'Administrator' || buildingIds.contains(b['id']) || lineIds.contains(line['id']),
            onChanged: busy || role == 'Administrator' || buildingIds.contains(b['id']) ? null : (selected) => setState(() { if (selected == true) { lineIds.add(line['id'] as int); } else { lineIds.remove(line['id']); } }),
          )),
        ],
        if (error != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(error!, style: const TextStyle(color: Colors.red))),
      ]))),
      actions: [TextButton(onPressed: busy ? null : () => Navigator.pop(context), child: const Text('Cancel')), FilledButton(onPressed: busy ? null : save, child: Text(busy ? 'Saving…' : widget.creating ? 'Create account' : 'Save account'))],
    );
  }
}

class PartEditor extends StatefulWidget {
  final Map<String, dynamic>? part;
  final List<Map<String, dynamic>> types;
  final Future<void> Function(Map<String, dynamic>) onSave;
  const PartEditor({super.key, this.part, required this.types, required this.onSave});
  @override State<PartEditor> createState() => _PartEditorState();
}
class _PartEditorState extends State<PartEditor> {
  static const labels = <String, String>{
    'name': 'Part name', 'sku': 'Unique SKU', 'bin': 'Storage bin',
    'supplier': 'Supplier (optional)', 'supplier_number': 'Supplier part number (optional)',
    'cost': 'Unit cost', 'threshold': 'Reorder threshold', 'target': 'Target stock',
    'lead_days': 'Supplier lead time (days)', 'interval_days': 'Expected replacement interval (days)',
  };
  late Map<String, TextEditingController> controllers;
  late Set<int> selectedTypes;
  bool busy = false;
  String? error;
  bool get creating => widget.part == null;
  @override void initState() {
    super.initState();
    final defaults = <String, dynamic>{'name': '', 'sku': '', 'bin': '', 'supplier': '', 'supplier_number': '', 'cost': 0, 'threshold': 0, 'target': 10, 'lead_days': 0, 'interval_days': 90, 'stock': 0, 'change_reason': ''};
    final values = {...defaults, ...?widget.part};
    controllers = {for (final key in [...labels.keys, if (creating) 'stock' else 'change_reason']) key: TextEditingController(text: '${values[key]}')};
    selectedTypes = (widget.part?['type_ids'] as List? ?? []).cast<int>().toSet();
  }
  @override void dispose() {
    for (final controller in controllers.values) { controller.dispose(); }
    super.dispose();
  }
  Future<void> save() async {
    setState(() { busy = true; error = null; });
    try {
      final data = <String, dynamic>{};
      for (final key in controllers.keys) {
        final text = controllers[key]!.text.trim();
        if (['supplier', 'supplier_number'].contains(key)) { data[key] = text; continue; }
        if (text.isEmpty) throw Exception('${labels[key] ?? (key == 'stock' ? 'Opening stock' : 'Change reason')} is required.');
        if (['threshold', 'target', 'lead_days', 'interval_days', 'stock'].contains(key)) {
          final value = int.tryParse(text);
          if (value == null || value < (key == 'interval_days' ? 1 : 0)) throw Exception('${labels[key] ?? 'Opening stock'} must be a valid whole number.');
          data[key] = value;
        } else if (key == 'cost') {
          final value = double.tryParse(text);
          if (value == null || !value.isFinite || value < 0) throw Exception('Enter a valid nonnegative unit cost.');
          data[key] = value;
        } else { data[key] = text; }
      }
      if (selectedTypes.isEmpty) throw Exception('Select at least one compatible machine type.');
      if ((data['target'] as int) < (data['threshold'] as int)) throw Exception('Target stock must be at least the reorder threshold.');
      data['type_ids'] = selectedTypes.toList()..sort();
      if (!creating) { data['part_id'] = widget.part!['id']; data['revision'] = widget.part!['revision'] ?? 0; }
      await widget.onSave(data);
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => AlertDialog(
    title: Text(creating ? 'Add compatible part' : 'Edit part · ${widget.part!['name']}'),
    content: SizedBox(width: 560, child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      if (!creating) Text('Shared stock: ${widget.part!['stock']}. Use Receive or Adjust to change quantity. Completed replacement costs stay unchanged.'),
      for (final entry in labels.entries) Padding(padding: const EdgeInsets.only(top: 14), child: TextField(controller: controllers[entry.key], enabled: !busy, keyboardType: ['cost', 'threshold', 'target', 'lead_days', 'interval_days'].contains(entry.key) ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text, decoration: InputDecoration(labelText: entry.value))),
      const SizedBox(height: 18),
      const Text('Compatible machine types', style: TextStyle(fontWeight: FontWeight.bold)),
      const Text('One physical stock balance is shared across these types.'),
      for (final type in widget.types) CheckboxListTile(key: ValueKey('part-type:${type['id']}'), contentPadding: EdgeInsets.zero, title: Text(type['name'] as String), value: selectedTypes.contains(type['id']), onChanged: busy ? null : (checked) => setState(() { if (checked == true) { selectedTypes.add(type['id'] as int); } else { selectedTypes.remove(type['id']); } })),
      const SizedBox(height: 10),
      TextField(controller: controllers[creating ? 'stock' : 'change_reason'], enabled: !busy, keyboardType: creating ? TextInputType.number : TextInputType.text, decoration: InputDecoration(labelText: creating ? 'Opening stock' : 'Change reason (required)')),
      if (error != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(error!, style: const TextStyle(color: Colors.red))),
    ]))),
    actions: [TextButton(onPressed: busy ? null : () => Navigator.pop(context), child: const Text('Cancel')), FilledButton(onPressed: busy ? null : save, child: Text(busy ? 'Saving…' : creating ? 'Add part' : 'Save details'))],
  );
}
