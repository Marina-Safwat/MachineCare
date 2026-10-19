import 'dart:convert';
import 'package:flutter/material.dart';
import 'api.dart';
import 'file_export.dart';
import 'design.dart';

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
  final Map<String, String>? options;
  EntryField(this.key, this.label, this.controller, {this.number = false, this.decimal = false, this.secret = false, this.optional = false, this.options});
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
    if (busy) return;
    setState(() { busy = true; error = null; });
    try {
      final d = <String, dynamic>{};
      for (final f in widget.fields) {
        final v = f.controller.text;
        if (!f.optional && v.trim().isEmpty) throw Exception('${f.label} is required.');
        if (f.number && int.tryParse(v) == null) throw Exception('${f.label}: enter a whole number.');
        if (f.decimal && (double.tryParse(v) == null || !double.parse(v).isFinite)) throw Exception('${f.label}: enter a valid amount.');
        d[f.key] = f.number ? int.parse(v) : f.decimal ? double.parse(v) : v;
      }
      await widget.onSave(d);
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => AlertDialog(title: Text(widget.title), content: SizedBox(width: 480, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
    if (widget.intro != null) widget.intro!,
    for (final f in widget.fields) Padding(padding: const EdgeInsets.only(top: 14), child: f.options != null ? DropdownButtonFormField<String>(isExpanded: true, value: f.options!.containsKey(f.controller.text) ? f.controller.text : null, decoration: InputDecoration(labelText: f.label), items: f.options!.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value, overflow: TextOverflow.ellipsis))).toList(), onChanged: busy ? null : (v) => f.controller.text = v ?? '') : TextField(controller: f.controller, obscureText: f.secret, enabled: !busy, keyboardType: f.number || f.decimal ? const TextInputType.numberWithOptions(signed: true, decimal: true) : TextInputType.text, decoration: InputDecoration(labelText: f.label))),
    if (error != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(error!, style: const TextStyle(color: Color(0xffb3261e)))),
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
  static const pages = ['Overview', 'Equipment', 'Inventory', 'Approvals', 'History', 'Management', 'Notifications', 'Reorders', 'Audit log', 'Stock movements', 'Reports'];
  static const icons = [Icons.dashboard_outlined, Icons.precision_manufacturing_outlined, Icons.inventory_2_outlined, Icons.fact_check_outlined, Icons.history, Icons.settings_outlined, Icons.notifications_outlined, Icons.shopping_cart_outlined, Icons.manage_search, Icons.swap_vert, Icons.download_outlined];
  String reorderFilter = 'Active';
  bool get purchasingAllowed => ['Administrator', 'Lead'].contains(state['user']?['role']);
  bool get admin => state['user']?['role'] == 'Administrator';
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async {
    if (mounted) setState(() { loading = true; error = null; });
    try { final s = await widget.api.call('/state'); if (mounted) setState(() => state = s); }
    catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => loading = false); }
  }
  bool acting = false;
  Future<void> act(String name, Map<String, dynamic> d) async {
    if (acting) return;
    acting = true;
    try {
      if (['cancel', 'disable'].contains(name) && !await confirmAction(context, name == 'cancel' ? 'Cancel maintenance request?' : 'Change account availability?', name == 'cancel' ? 'This releases any reserved parts. Physical stock will not change.' : 'Disabling an account revokes its sessions. Confirm this employee account change.')) return;
      await widget.api.action(name, d); await refresh();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Changes saved.')));
    }
    catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(cleanError(e)))); }
    finally { acting = false; }
  }
  Future<void> form(String title, String action, List<List<String>> specs, {Map<String, dynamic> extra = const {}, String? intro}) async {
    Map<String, String>? options(String key) {
      if (key == 'building_id') return {for (final b in rows(state, 'buildings')) '${b['id']}': '${b['code']} · ${b['name']}'};
      if (key == 'line_id') return {for (final l in rows(state, 'lines')) '${l['id']}': '${rows(state, 'buildings').where((b) => b['id'] == l['building_id']).map((b) => b['code']).join()} · ${l['code']}'};
      if (key == 'type_id') return {for (final t in rows(state, 'types')) '${t['id']}': '${t['name']}'};
      if (key == 'status') return {for (final s in ['Operating', 'Maintenance', 'Stopped', 'Retired']) s: s};
      return null;
    }
    final fields = specs.map((s) => EntryField(s[0], s[1].replaceAll('Building ID', 'Building').replaceAll('Line ID', 'Production line').replaceAll('Machine type ID', 'Machine type'), TextEditingController(text: s.length > 3 ? s[3] : ''), number: s.length > 2 && s[2] == 'int', decimal: s.length > 2 && s[2] == 'decimal', secret: s[0].contains('password'), optional: s.length > 2 && s[2] == 'optional', options: options(s[0]))).toList();
    await showDialog<bool>(context: context, builder: (_) => EntryDialog(title: title, fields: fields, intro: intro == null ? null : Text(intro), onSave: (d) async { if (action == 'part') { d['type_ids'] = (d['type_ids'] as String).split(',').map((v) => int.parse(v.trim())).toList(); } if (['adjust', 'reorder_cancel'].contains(action) && !await confirmAction(context, 'Confirm $title', action == 'adjust' ? 'Change physical stock by ${d['delta']} units? Reason: ${d['reason']}' : 'Cancel the remaining order balance? Previously received stock is kept.')) throw Exception('No changes saved. Review the values before confirming.'); await widget.api.action(action, {...extra, ...d}); }));
    if (!mounted) return;
    await refresh();
  }
  bool get compact => MediaQuery.sizeOf(context).width < 600;
  double get factWidth => compact ? 140 : 190;
  Widget labelled(String label, String value) => Text.rich(TextSpan(children: [TextSpan(text: '$label: ', style: const TextStyle(fontWeight: FontWeight.w700)), TextSpan(text: value)]));
  Widget panel(String title, List<Widget> children, {Widget? trailing, String? subtitle}) => Card(child: Padding(padding: EdgeInsets.all(compact ? 16 : 22), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: Theme.of(context).textTheme.titleLarge), if (subtitle != null) Padding(padding: const EdgeInsets.only(top: 4), child: Text(subtitle, style: const TextStyle(color: Palette.muted)))])), if (trailing != null) ...[const SizedBox(width: 12), trailing]]), const SizedBox(height: 14), ...children])));
  Widget pill(String text) => StatusPill(text);
  Widget overview() {
    final machines = rows(state, 'machines'), parts = rows(state, 'parts'), requests = rows(state, 'requests'), history = rows(state, 'history');
    final low = parts.where((p) => (p['available_quantity'] ?? p['stock']) <= p['threshold']).toList();
    final pending = requests.where((r) => r['state'] == 'Pending').length;
    final ready = requests.where((r) => r['state'] == 'Approved').length;
    final alerts = rows(state, 'alerts').where((a) => a['resolved'] == null).length;
    final spend = history.fold<double>(0, (sum, h) => sum + (h['quantity'] as num) * (h['unit_cost'] as num));
    int overdue = 0;
    for (final m in machines) { for (final p in (m['parts'] as List)) { if (p['last_replacement'] != null && DateTime.now().difference(DateTime.parse(p['last_replacement'] as String)).inDays >= (p['interval_days'] as int)) overdue++; } }
    final open = rows(state, 'reorders').where((r) => ['Approved', 'Ordered', 'Partially received'].contains(r['state'])).length;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Keep production moving.', style: Theme.of(context).textTheme.headlineMedium), const SizedBox(height: 6),
      const Text('One place for equipment, replacement decisions, and shared spare parts. Start with anything highlighted.', style: TextStyle(color: Palette.muted, fontSize: 16)), const SizedBox(height: 22),
      Wrap(spacing: 14, runSpacing: 14, children: [
        metric('Machines', '${machines.length}', Icons.precision_manufacturing_outlined, note: '${machines.where((m) => m['status'] == 'Operating').length} operating', onTap: () => setState(() => page = 1)),
        metric('Low-stock SKUs', '${low.length}', Icons.inventory_2_outlined, tone: low.isEmpty ? Tone.ok : Tone.warn, note: low.isEmpty ? 'All above threshold' : 'Plan reorders', onTap: () => setState(() { page = 2; lowOnly = low.isNotEmpty; })),
        metric('Pending approvals', '$pending', Icons.fact_check_outlined, tone: pending > 0 ? Tone.warn : Tone.ok, note: pending > 0 ? 'Waiting for a lead' : '$ready ready to complete', onTap: () => setState(() => page = 3)),
        metric('Active alerts', '$alerts', Icons.notifications_active_outlined, tone: alerts > 0 ? Tone.danger : Tone.ok, note: alerts > 0 ? 'Open conditions' : 'All clear', onTap: () => setState(() => page = 6)),
        if (purchasingAllowed) metric('Outstanding reorders', '$open', Icons.local_shipping_outlined, note: 'Approved or on order', onTap: () => setState(() => page = 7)),
        metric('Recorded spending', '\$${spend.toStringAsFixed(2)}', Icons.payments_outlined, note: 'From completed work'),
      ]),
      const SizedBox(height: 22),
      panel('Production status', [
        Wrap(spacing: 10, runSpacing: 10, children: ['Operating', 'Maintenance', 'Stopped', 'Retired'].map((s) => StatusPill('$s: ${machines.where((m) => m['status'] == s).length}', tone: toneFor(s))).toList()),
        const SizedBox(height: 14),
        overdue > 0 ? Notice('$overdue machine/part intervals overdue. No history means due date unknown.', tone: Tone.warn) : const Text('0 machine/part intervals overdue. No history means due date unknown.', style: TextStyle(color: Palette.muted)),
      ]),
      panel('Stock needs attention', [
        if (low.isEmpty) const EmptyState('No low-stock parts.', icon: Icons.check_circle_outline),
        for (final p in low) Padding(padding: const EdgeInsets.only(bottom: 16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Padding(padding: EdgeInsets.only(top: 2, right: 10), child: Icon(Icons.warning_amber_rounded, color: Palette.warnFg)),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(p['name'] as String, style: Theme.of(context).textTheme.titleSmall), Text('${p['sku']} • ${p['bin']}', style: Theme.of(context).textTheme.bodySmall), Text('${p['available_quantity'] ?? p['stock']} available / ${p['threshold']} threshold', style: const TextStyle(fontWeight: FontWeight.w700, color: Palette.warnFg))])),
          ]),
          const SizedBox(height: 8),
          StockBar(available: (p['available_quantity'] ?? p['stock']) as num, threshold: p['threshold'] as num, target: p['target'] as num),
        ])),
      ]),
      panel('Recent replacements', [
        if (history.isEmpty) const EmptyState('No completed replacements yet.', icon: Icons.history),
        for (final h in history.take(5)) ListTile(contentPadding: EdgeInsets.zero, leading: const CircleAvatar(radius: 18, backgroundColor: Palette.brandSoft, child: Icon(Icons.build_outlined, size: 18, color: Palette.brand)), title: Text('${h['part']} • ${h['location_snapshot']}', style: const TextStyle(fontWeight: FontWeight.w600)), subtitle: Text('${date(h['replaced'])} • ${h['technician']} • Qty ${h['quantity']}')),
      ]),
      const Notice('Pilot: in-app notifications available. Email requires administrator setup. Supplier ordering remains a manual step.', tone: Tone.neutral),
    ]);
  }
  Widget metric(String label, String value, IconData icon, {Tone tone = Tone.neutral, String? note, VoidCallback? onTap}) {
    final s = toneStyle(tone);
    final accent = tone == Tone.neutral ? Palette.brand : s.fg;
    final width = compact ? (MediaQuery.sizeOf(context).width - 24 - 14) / 2 - 1 : 224.0;
    return SizedBox(width: width, child: Card(margin: EdgeInsets.zero, clipBehavior: Clip.antiAlias, child: InkWell(onTap: onTap, child: Padding(padding: EdgeInsets.all(compact ? 14 : 20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: tone == Tone.neutral ? Palette.brandSoft : s.bg, borderRadius: BorderRadius.circular(10)), child: Icon(icon, color: accent, size: 22)),
      const SizedBox(height: 14),
      FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft, child: Text(value, style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800, color: Palette.ink))),
      Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
      if (note != null) Padding(padding: const EdgeInsets.only(top: 4), child: Text(note, style: TextStyle(fontSize: 13, color: tone == Tone.neutral ? Palette.muted : s.fg, fontWeight: FontWeight.w600))),
    ])))));
  }
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
      if (ms.isEmpty) const EmptyState('No machines match these filters. Clear filters or choose another location.', icon: Icons.search_off),
      for (final b in buildings.where((b) => ms.any((m) => m['building_id'] == b['id']))) Card(child: ExpansionTile(key: ValueKey('building:${b['id']}:$active'), leading: const Icon(Icons.apartment_outlined, color: Palette.brand), title: Text('${b['code']} · ${b['name']}', style: Theme.of(context).textTheme.titleMedium), initiallyExpanded: true, children: [
        for (final l in lines.where((l) => l['building_id'] == b['id'] && ms.any((m) => m['line_id'] == l['id']))) ExpansionTile(key: ValueKey('line:${l['id']}:$active'), leading: const Icon(Icons.account_tree_outlined), title: Text('Line ${l['code']}', style: const TextStyle(fontWeight: FontWeight.w600)), subtitle: Text('${ms.where((m) => m['line_id'] == l['id']).length} machines'), initiallyExpanded: active, children: [
          for (final t in types.where((t) => ms.any((m) => m['line_id'] == l['id'] && m['type_id'] == t['id']))) ExpansionTile(title: Text(t['name'] as String), initiallyExpanded: true, children: [
            for (final m in ms.where((m) => m['line_id'] == l['id'] && m['type_id'] == t['id'])) ListTile(leading: const Icon(Icons.precision_manufacturing_outlined), title: Text(m['name'] as String, style: const TextStyle(fontWeight: FontWeight.w600)), subtitle: Text('Asset ${m['asset_tag']}'), trailing: pill(m['status'] as String), onTap: () => machineDetails(m)),
          ]),
        ]),
      ])),
    ]);
  }
  Future<void> machineDetails(Map<String, dynamic> m) async {
    final route = DialogRoute<Map<String, dynamic>>(context: context, builder: (ctx) => AlertDialog(title: Text(m['name'] as String), content: SizedBox(width: 680, child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, runSpacing: 8, children: [pill(m['status'] as String), StatusPill('Asset ${m['asset_tag']}', tone: Tone.neutral, icon: Icons.sell_outlined), if ('${m['serial'] ?? ''}'.isNotEmpty) StatusPill('Serial ${m['serial']}', tone: Tone.neutral, icon: Icons.tag)]),
      const SectionLabel('Compatible parts · shared inventory'),
      for (final p in (m['parts'] as List)) Card(margin: const EdgeInsets.only(bottom: 10), child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${p['name']} · ${p['sku']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)), const SizedBox(height: 10),
        FactGrid([Fact('Available', '${p['available_quantity'] ?? p['stock']}', width: 110), Fact('Reserved', '${p['reserved_quantity'] ?? 0}', width: 110), Fact('Bin', '${p['bin']}', width: 150), Fact('Last replacement', date(p['last_replacement']), width: 150), Fact('Expected life', '${p['interval_days']} days', width: 130)]),
        Align(alignment: Alignment.centerRight, child: FilledButton.tonalIcon(onPressed: m['status'] == 'Retired' ? null : () => Navigator.pop(ctx, Map<String, dynamic>.from(p as Map)), icon: const Icon(Icons.build_outlined), label: const Text('Replace this part')))]))),
      const SectionLabel('Requests'),
      if (!rows(state, 'requests').any((r) => r['machine_id'] == m['id'])) const Text('No requests for this machine.', style: TextStyle(color: Palette.muted)),
      for (final r in rows(state, 'requests').where((r) => r['machine_id'] == m['id'])) Padding(padding: const EdgeInsets.only(bottom: 6), child: Wrap(spacing: 10, crossAxisAlignment: WrapCrossAlignment.center, children: [Text('#${r['id']} ${r['part']}', style: const TextStyle(fontWeight: FontWeight.w600)), pill(r['state'] as String)])),
      const SectionLabel('Maintenance history'),
      if (!rows(state, 'history').any((h) => h['machine_id'] == m['id'])) const Text('No completed work recorded.', style: TextStyle(color: Palette.muted)),
      for (final h in rows(state, 'history').where((h) => h['machine_id'] == m['id'])) Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('${date(h['replaced'])} • ${h['part']} • ${h['technician']}')),
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
    await form(early ? (purchasingAllowed ? 'Early replacement · manager confirmation' : 'Early replacement • lead approval required') : 'Request replacement', 'request', [ ['quantity', 'Quantity', 'int', '1'], ['reason', 'Reason'], ['notes', 'Notes', 'optional'], if (early) ['early_explanation', 'Required early replacement explanation'] ], extra: {'machine_id': m['id'], 'part_id': p['id'], 'operation_key': 'request:${DateTime.now().microsecondsSinceEpoch}:${state['user']['id']}'}, intro: '${m['name']}\n${p['name']} • ${p['available_quantity'] ?? p['stock']} available (${p['reserved_quantity'] ?? 0} reserved) at ${p['bin']}\nPrevious: ${date(last)} • expected ${p['interval_days']} days\n${early ? 'WARNING: only $elapsed days elapsed. ${purchasingAllowed ? 'Manager request is approved with the required explanation.' : 'A Lead must approve before completion.'}' : 'No early replacement detected.'}\nApproved work reserves stock without deducting physical inventory. Pending early work reserves nothing until approved. Record completion after physical work.');
  }
  String inventorySearch = '';
  bool lowOnly = false;
  Widget inventory() {
    final all = rows(state, 'parts');
    bool isLow(Map<String, dynamic> p) => (p['available_quantity'] ?? p['stock']) <= p['threshold'];
    final visible = all.where((p) => (!lowOnly || isLow(p)) && '${p['name']} ${p['sku']} ${p['supplier']} ${p['bin']} ${p['provenance'] ?? ''}'.toLowerCase().contains(inventorySearch)).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(child: TextField(decoration: const InputDecoration(labelText: 'Search parts, SKU, supplier or bin', prefixIcon: Icon(Icons.search)), onChanged: (v) => setState(() => inventorySearch = v.toLowerCase()))),
        if (purchasingAllowed) ...[const SizedBox(width: 12), FilledButton.icon(onPressed: addPart, icon: const Icon(Icons.add), label: const Text('Add part'))],
      ]),
      const SizedBox(height: 12),
      Wrap(spacing: 12, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
        FilterChip(label: Text('Low stock only (${all.where(isLow).length})'), selected: lowOnly, onSelected: (v) => setState(() => lowOnly = v)),
        Text('Showing ${visible.length} of ${all.length} parts', style: const TextStyle(color: Palette.muted, fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 16),
      if (all.isEmpty) const EmptyState('No parts have been added yet.', icon: Icons.inventory_2_outlined) else if (visible.isEmpty) const EmptyState('No parts match this search.', icon: Icons.search_off),
      for (final p in visible) partCard(p),
    ]);
  }
  Widget stockStat(String label, Object value, {Tone? tone}) => Container(
    width: compact ? 96 : 118, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    decoration: BoxDecoration(color: tone == null ? Palette.subtle : toneStyle(tone).bg, borderRadius: BorderRadius.circular(10), border: Border.all(color: tone == null ? Palette.border : Colors.transparent)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: tone == null ? Palette.muted : toneStyle(tone).fg)), Text('$value', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: tone == null ? Palette.ink : toneStyle(tone).fg))]),
  );
  Widget partCard(Map<String, dynamic> p) {
    final available = (p['available_quantity'] ?? p['stock']) as num;
    final low = available <= (p['threshold'] as num);
    final provenance = p['provenance'] as Map?;
    return panel(p['name'] as String, [
      Wrap(spacing: 8, runSpacing: 8, children: [StatusPill(p['sku'] as String, tone: Tone.neutral, icon: Icons.qr_code_2), if (low) const StatusPill('Low stock', tone: Tone.warn, icon: Icons.warning_amber_rounded), if (provenance != null) pill('Demo stock / planning values')]),
      const SizedBox(height: 16),
      Wrap(spacing: 10, runSpacing: 10, children: [stockStat('Physical', p['stock']), stockStat('Reserved', p['reserved_quantity'] ?? 0), stockStat('Available', available, tone: available <= 0 ? Tone.danger : low ? Tone.warn : Tone.ok)]),
      const SizedBox(height: 12),
      StockBar(available: available, threshold: p['threshold'] as num, target: p['target'] as num),
      const SizedBox(height: 6),
      Text('Reorder at ${p['threshold']} · target ${p['target']} · bar marks the reorder level', style: Theme.of(context).textTheme.bodySmall),
      if (low) const Padding(padding: EdgeInsets.only(top: 12), child: Notice('Low stock: available is at or below the reorder threshold. Plan a reorder.', tone: Tone.warn, icon: Icons.warning_amber_rounded)),
      if ((p['reservation_shortfall'] ?? 0) > 0) Padding(padding: const EdgeInsets.only(top: 12), child: Notice('Reservation shortfall: ${p['reservation_shortfall']} units. Receive stock or cancel approved work.', tone: Tone.danger)),
      const SizedBox(height: 16),
      FactGrid([
        Fact('Bin', '${p['bin']}', width: factWidth), Fact('Unit cost', '\$${(p['cost'] as num).toStringAsFixed(2)}', width: factWidth),
        Fact('Supplier', '${p['supplier'] ?? ''}'.isEmpty ? 'Not provided' : '${p['supplier']}', width: factWidth), Fact('Expected life', '${p['interval_days']} days', width: factWidth),
        Fact('Suggested order', '${p['suggested_order_quantity'] ?? 0}', width: factWidth), Fact('On order', '${p['outstanding_order_quantity'] ?? 0}', width: factWidth), Fact('Pending requests', '${p['pending_reorder_quantity'] ?? 0}', width: factWidth),
      ]),
      if (provenance != null) Container(margin: const EdgeInsets.only(top: 16), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Palette.subtle, borderRadius: BorderRadius.circular(10), border: Border.all(color: Palette.border)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Supplied reference', style: TextStyle(fontWeight: FontWeight.w700)), const SizedBox(height: 6),
        Text('Manufacturer: ${provenance['manufacturer'] ?? 'Unknown'}'),
        Text('Part number: ${provenance['manufacturer_part_number'] ?? 'Not supplied'}'),
        if (provenance['reference_serial'] != null) Text('Supplied serial reference: ${provenance['reference_serial']} (not a part number)'),
        Text('Used per machine: ${provenance['quantity_per_machine']} | ${provenance['machine_family']}'),
        const SizedBox(height: 8),
        Text(provenance['demo_notice'] as String, style: Theme.of(context).textTheme.bodySmall),
      ])),
      if (purchasingAllowed) ...[
        const Divider(height: 28),
        Wrap(spacing: 8, runSpacing: 8, children: [
          FilledButton.tonalIcon(onPressed: () => requestReorder(p), icon: const Icon(Icons.add_shopping_cart), label: const Text('Request reorder')),
          TextButton.icon(onPressed: () => editPart(p), icon: const Icon(Icons.edit_outlined), label: const Text('Edit details')),
          TextButton.icon(onPressed: () => form('Receive stock', 'receipt', [['quantity', 'Received quantity', 'int'], ['reason', 'Receipt reference / reason']], extra: {'part_id': p['id'], 'operation_key': 'receipt:${DateTime.now().microsecondsSinceEpoch}'}), icon: const Icon(Icons.move_to_inbox_outlined), label: const Text('Receive')),
          TextButton.icon(onPressed: () => form('Adjust inventory', 'adjust', [['delta', 'Signed adjustment (+ / −)', 'int'], ['reason', 'Required adjustment reason']], extra: {'part_id': p['id'], 'operation_key': 'adjust:${DateTime.now().microsecondsSinceEpoch}'}), icon: const Icon(Icons.tune), label: const Text('Adjust')),
        ]),
      ],
    ]);
  }
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
  Widget approvals() {
    final all = rows(state, 'requests');
    if (all.isEmpty) return const EmptyState('No replacement requests yet. Open a machine in Equipment to request a part.', icon: Icons.fact_check_outlined);
    final groups = [('Needs review', all.where((r) => r['state'] == 'Pending').toList()), ('Ready to complete', all.where((r) => r['state'] == 'Approved').toList()), ('Closed', all.where((r) => !['Pending', 'Approved'].contains(r['state'])).toList())];
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      for (final (label, items) in groups) if (items.isNotEmpty) ...[SectionLabel(label, count: items.length), for (final r in items) requestCard(r)],
    ]);
  }
  Widget requestCard(Map<String, dynamic> r) {
    final machine = rows(state, 'machines').where((m) => m['id'] == r['machine_id']).map((m) => m['name']).firstOrNull ?? 'Machine #${r['machine_id']}';
    final mine = r['technician_id'] == state['user']['id'];
    return panel('#${r['id']} · ${r['part']}', [
      Wrap(spacing: 8, runSpacing: 8, children: [pill(r['state'] as String), if (r['early'] == 1) pill('Early replacement')]),
      const SizedBox(height: 14),
      FactGrid([Fact('Machine', '$machine', width: compact ? 300 : 380), Fact('Quantity', '${r['quantity']}', width: 110), Fact('Requested by', '${r['technician']}', width: factWidth)]),
      const SizedBox(height: 12),
      labelled('Reason', r['reason'] as String),
      if ('${r['notes'] ?? ''}'.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: r['early'] == 1 ? Notice('${r['notes']}', tone: Tone.info, icon: Icons.chat_bubble_outline) : labelled('Notes', '${r['notes']}')),
      if (r['review_comment'] != null) Padding(padding: const EdgeInsets.only(top: 4), child: labelled('Lead comment', '${r['review_comment']}')),
      const SizedBox(height: 12),
      if (r['state'] == 'Approved') Notice('${r['quantity']} units reserved for this work.', tone: Tone.ok, icon: Icons.inventory_2_outlined),
      if (r['state'] == 'Pending') const Notice('No stock reserved until approval.', tone: Tone.warn),
      if (['Pending', 'Approved'].contains(r['state'])) const SizedBox(height: 14),
      Wrap(spacing: 10, runSpacing: 8, children: [if (r['state'] == 'Pending' && purchasingAllowed && !mine) ...[FilledButton.icon(onPressed: () => review(r, 'Approved'), icon: const Icon(Icons.check), label: const Text('Approve')), OutlinedButton(onPressed: () => review(r, 'Rejected'), child: const Text('Reject'))], if (r['state'] == 'Approved' && (purchasingAllowed || mine)) FilledButton.icon(onPressed: () => confirmComplete(r), icon: const Icon(Icons.task_alt), label: const Text('Record physical completion')), if (['Pending', 'Approved'].contains(r['state']) && (purchasingAllowed || mine)) TextButton(onPressed: () => act('cancel', {'request_id': r['id']}), child: const Text('Cancel request'))]),
    ]);
  }
  Future<void> review(Map<String, dynamic> r, String decision) => form('$decision request #${r['id']}', 'review', [['comment', 'Lead review comment']], extra: {'request_id': r['id'], 'decision': decision});
  Future<void> confirmComplete(Map<String, dynamic> r) async {
    final yes = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: const Text('Confirm physical replacement'), content: Text('Has quantity ${r['quantity']} of ${r['part']} actually been replaced? This records maintenance and deducts shared stock.'), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Back')), FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Yes, record completion'))]));
    if (yes == true) await act('complete', {'request_id': r['id']});
  }
  Widget history() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    const Padding(padding: EdgeInsets.fromLTRB(4, 0, 4, 14), child: Text('Completed work only. Location and cost are kept exactly as recorded at the time of the replacement.', style: TextStyle(color: Palette.muted))),
    if (rows(state, 'history').isEmpty) const EmptyState('No completed maintenance recorded.', icon: Icons.history),
    for (final h in rows(state, 'history')) panel(h['part'] as String, trailing: StatusPill(date(h['replaced']), tone: Tone.neutral, icon: Icons.event_outlined), [
      Text(h['location_snapshot'] as String, style: const TextStyle(color: Palette.muted, fontWeight: FontWeight.w500)),
      if (h['early'] == 1) const Padding(padding: EdgeInsets.only(top: 8), child: StatusPill('Early replacement')),
      const SizedBox(height: 14),
      FactGrid([Fact('Completed by', '${h['technician']}', width: factWidth), Fact('Quantity', '${h['quantity']}', width: factWidth), Fact('Recorded cost', '\$${((h['quantity'] as num) * (h['unit_cost'] as num)).toStringAsFixed(2)}', width: factWidth)]),
      const SizedBox(height: 12),
      labelled('Reason', h['reason'] as String),
    ]),
  ]);
  Widget administration() {
    if (!purchasingAllowed) return const Text('Lead or Administrator permission required.');
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (admin) panel('Buildings & lines', [Wrap(spacing: 12, children: [FilledButton.tonal(onPressed: () => form('Create building', 'building', [['code', 'Building code'], ['name', 'Building name']]), child: const Text('Add building')), FilledButton.tonal(onPressed: () => form('Create line', 'line', [['building_id', 'Building ID', 'int'], ['code', 'Line code'], ['description', 'Description (optional)', 'optional']]), child: const Text('Add line'))]), for (final b in rows(state, 'buildings')) ListTile(title: Text('#${b['id']} ${b['code']} · ${b['name']}'), trailing: IconButton(tooltip: 'Edit building', icon: const Icon(Icons.edit_outlined), onPressed: () => form('Edit building', 'building', [['code', 'Code', 'text', b['code'] as String], ['name', 'Name', 'text', b['name'] as String]], extra: {'id': b['id']}))), for (final l in rows(state, 'lines')) ListTile(title: Text('Line #${l['id']} • Building ${l['building_id']} • ${l['code']}'), subtitle: Text(l['description'] as String), trailing: IconButton(tooltip: 'Edit line', icon: const Icon(Icons.edit_outlined), onPressed: () => form('Edit line', 'line', [['building_id', 'Building ID', 'int', '${l['building_id']}'], ['code', 'Code', 'text', l['code'] as String], ['description', 'Description (optional)', 'optional', l['description'] as String]], extra: {'id': l['id']})))]),
      panel('Machine types', [FilledButton.tonal(onPressed: () => form('Add machine type', 'type', [['name', 'Machine type name']]), child: const Text('Add type')), for (final t in rows(state, 'types')) ListTile(title: Text(t['name'] as String), subtitle: Text('Type ID ${t['id']}'), trailing: IconButton(tooltip: 'Rename machine type', icon: const Icon(Icons.edit_outlined), onPressed: () => form('Rename machine type', 'type', [['name', 'Machine type name', 'text', t['name'] as String]], extra: {'id': t['id'], 'revision': t['revision'] ?? 0}, intro: 'Machine assignments and compatible parts keep their existing links. Recorded maintenance locations keep their original names.'))) ]),
      panel('Equipment registry', [FilledButton.tonal(onPressed: () => editMachine(null), child: const Text('Register machine')), for (final m in rows(state, 'machines')) ListTile(title: Text(m['name'] as String), subtitle: Text('Machine ID ${m['id']}'), trailing: IconButton(tooltip: 'Edit, move or retire machine', icon: const Icon(Icons.edit_outlined), onPressed: () => editMachine(m)))]),
      if (admin) SystemStatus(api: widget.api),
      if (admin) panel('Accounts', [FilledButton.tonal(onPressed: createUser, child: const Text('Create employee account')), for (final u in rows(state, 'users')) ListTile(title: Text('${u['username']} · ${u['role']}'), subtitle: Text('ID ${u['id']} • Lead ${u['lead_id'] ?? 'unassigned'} • ${u['active'] == 1 ? 'Active' : 'Disabled'}'), trailing: u['id'] == state['user']['id'] ? null : Wrap(children: [IconButton(tooltip: 'Edit role, lead, building and line access', icon: const Icon(Icons.edit_outlined), onPressed: () => editUser(u)), IconButton(tooltip: 'Reset password', icon: const Icon(Icons.key), onPressed: () => form('Reset employee password', 'reset', [['password', 'Temporary password (12+ characters)']], extra: {'user_id': u['id']})), IconButton(tooltip: u['active'] == 1 ? 'Disable' : 'Enable', icon: Icon(u['active'] == 1 ? Icons.block : Icons.check_circle_outline), onPressed: () => act('disable', {'user_id': u['id'], 'active': u['active'] == 1 ? 0 : 1}))]))]),
    ]);
  }
  Future<void> editMachine(Map<String, dynamic>? m) => form(m == null ? 'Register machine' : 'Edit / move / retire machine', 'machine', [['line_id', 'Line ID', 'int', '${m?['line_id'] ?? ''}'], ['type_id', 'Machine type', 'int', '${m?['type_id'] ?? ''}'], ['station', 'Station / position within line', 'text', '${m?['station'] ?? ''}'], ['asset_tag', 'Unique asset tag', 'text', '${m?['asset_tag'] ?? ''}'], ['serial', 'Serial number', 'optional', '${m?['serial'] ?? ''}'], ['status', 'Operating status', 'text', '${m?['status'] ?? 'Operating'}']], extra: {if (m != null) 'id': m['id']});
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
  Future<void> requestReorder([Map<String, dynamic>? part]) async {
    final parts = rows(state, 'parts');
    if (parts.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Add inventory parts before requesting an order.')));
      return;
    }
    final key = 'reorder:${DateTime.now().microsecondsSinceEpoch}:${state['user']['id']}';
    await showDialog<bool>(context: context, builder: (_) => ReorderRequestEditor(
      parts: parts, initialPartId: part?['id'] as int?,
      onSave: (data) async { await widget.api.action('reorder_request', {...data, 'operation_key': key}); },
    ));
    if (!mounted) return;
    await refresh();
  }
  Widget reorders() {
    if (!purchasingAllowed) return const Text('Purchasing requires Lead or Administrator access.');
    final all = rows(state, 'reorders');
    final visible = all.where((r) => reorderFilter == 'All' || (reorderFilter == 'Active' ? ['Requested', 'Approved', 'Ordered', 'Partially received'].contains(r['state']) : r['state'] == reorderFilter)).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      panel('Reorders & deliveries', subtitle: 'Lead requests are approved immediately. Administrator requests need another Lead or Administrator’s approval. Leads and Administrators record ordering, deliveries and cancellations.', [
        Wrap(spacing: 16, runSpacing: 12, children: [FilledButton.icon(onPressed: () => requestReorder(), icon: const Icon(Icons.add_shopping_cart), label: const Text('Request reorder')), SizedBox(width: 240, child: DropdownButtonFormField<String>(isExpanded: true, value: reorderFilter, decoration: const InputDecoration(labelText: 'Status'), items: ['Active', 'All', 'Requested', 'Approved', 'Ordered', 'Partially received', 'Received', 'Rejected', 'Cancelled'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(), onChanged: (s) => setState(() => reorderFilter = s!)))]),
      ]),

      if (visible.isEmpty) const EmptyState('No reorders match this status.', icon: Icons.local_shipping_outlined),
      for (final r in visible) panel('Reorder #${r['id']} · ${r['part']}', [
        Wrap(spacing: 8, runSpacing: 8, children: [pill(r['state'] as String), StatusPill(r['sku'] as String, tone: Tone.neutral, icon: Icons.qr_code_2)]),
        const SizedBox(height: 16),
        Text('${r['received_quantity']} of ${r['quantity']} received', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 6),
        ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(minHeight: 8, value: (r['quantity'] as int) == 0 ? 0 : (r['received_quantity'] as int) / (r['quantity'] as int), backgroundColor: Palette.neutralBg, color: r['state'] == 'Cancelled' ? Palette.muted : Palette.brand)),
        const SizedBox(height: 16),
        FactGrid([
          Fact('Requested', '${r['quantity']}', width: factWidth),
          Fact(r['state'] == 'Cancelled' ? 'Cancelled remainder' : 'Remaining', '${(r['quantity'] as int) - (r['received_quantity'] as int)}', width: factWidth),
          Fact('Requester', '${r['requester']} · ${date(r['created'])}', width: factWidth),
          Fact('Supplier at request', (r['supplier_snapshot'] as String).isEmpty ? 'Not provided' : r['supplier_snapshot'] as String, width: factWidth),
          Fact('Supplier part', '${r['supplier_number_snapshot'] ?? ''}'.isEmpty ? '—' : '${r['supplier_number_snapshot']}', width: factWidth),
          Fact('Est. value (excl. freight/tax)', '\$${((r['quantity'] as num) * (r['unit_cost_snapshot'] as num)).toStringAsFixed(2)}', width: factWidth),
          if (r['po_reference'] != null) Fact('Order / PO reference', '${r['po_reference']}', width: factWidth),
        ]),
        const SizedBox(height: 14),
        labelled('Reason', '${r['reason']}'),
        if (r['review_comment'] != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text('Review: ${r['review_comment']}', style: const TextStyle(color: Palette.muted))),
        if (r['cancellation_reason'] != null) Padding(padding: const EdgeInsets.only(top: 6), child: labelled('Cancellation', '${r['cancellation_reason']}')),
        if (r['state'] == 'Requested' && r['requested_by'] == state['user']['id']) const Padding(padding: EdgeInsets.only(top: 10), child: Notice('Another Lead or Administrator must review your request.', tone: Tone.warn)),
        const SizedBox(height: 14),
        Wrap(spacing: 10, runSpacing: 8, children: [
          if (purchasingAllowed && r['state'] == 'Requested' && r['requested_by'] != state['user']['id']) ...[
            FilledButton(onPressed: () => reviewReorder(r, 'Approved'), child: const Text('Approve order')),
            OutlinedButton(onPressed: () => reviewReorder(r, 'Rejected'), child: const Text('Reject order')),
          ],
          if (purchasingAllowed && r['state'] == 'Approved') FilledButton.tonal(onPressed: () => form('Record ordering · #${r['id']}', 'reorder_order', [['po_reference', 'Order / PO reference']], extra: {'reorder_id': r['id'], 'revision': r['revision']}, intro: 'Record this only after the order has been placed through your purchasing process. This app does not send an order to the supplier.'), child: const Text('Mark ordered')),
          if (purchasingAllowed && ['Ordered', 'Partially received'].contains(r['state'])) FilledButton(onPressed: () => receiveReorder(r), child: const Text('Receive delivery')),
          if (['Requested', 'Approved', 'Ordered', 'Partially received'].contains(r['state']) && purchasingAllowed) TextButton(onPressed: () => form('Cancel remaining order · #${r['id']}', 'reorder_cancel', [['reason', 'Required cancellation reason']], extra: {'reorder_id': r['id'], 'revision': r['revision']}, intro: 'Received stock is retained. The unreceived balance is cancelled. If already ordered, arrange cancellation with the supplier separately.'), child: const Text('Cancel remaining')),
        ]),
        const Divider(height: 24),
        ExpansionTile(title: const Text('Delivery history'), children: [
          if (!rows(state, 'deliveries').any((d) => d['reorder_id'] == r['id'])) const ListTile(title: Text('No deliveries recorded.')),
          for (final d in rows(state, 'deliveries').where((d) => d['reorder_id'] == r['id'])) ListTile(title: Text('${d['delivery_reference']} • Qty ${d['quantity']}'), subtitle: Text('${date(d['received'])} • ${d['receiver']} • ${d['notes']}')),
        ]),
      ]),
    ]);
  }
  Future<void> reviewReorder(Map<String, dynamic> r, String decision) => form('$decision reorder #${r['id']}', 'reorder_review', [['comment', 'Review comment']], extra: {'reorder_id': r['id'], 'revision': r['revision'], 'decision': decision});
  Future<void> receiveReorder(Map<String, dynamic> r) => form('Receive delivery · #${r['id']}', 'reorder_receive', [['quantity', 'Quantity physically received', 'int'], ['delivery_reference', 'Unique delivery reference for this order'], ['notes', 'Delivery notes', 'optional']], extra: {'reorder_id': r['id'], 'operation_key': 'delivery:${DateTime.now().microsecondsSinceEpoch}:${state['user']['id']}'}, intro: '${r['part']} • ${(r['quantity'] as int) - (r['received_quantity'] as int)} units remaining. Use a distinct packing-slip/item reference for each delivery. Only record stock that physically arrived.');
  Widget maintenancePlan() {
    final due = <Map<String, dynamic>>[];
    var unknown = 0;
    for (final m in rows(state, 'machines').where((m) => m['status'] != 'Retired')) {
      for (final p in rows(m, 'parts')) {
        final last = DateTime.tryParse('${p['last_replacement']}');
        if (last == null) { unknown++; continue; }
        final date = last.add(Duration(days: p['interval_days'] as int));
        if (date.isBefore(DateTime.now().toUtc().add(const Duration(days: 30)))) due.add({'machine': m['name'], 'part': p['name'], 'due': date});
      }
    }
    due.sort((a, b) => (a['due'] as DateTime).compareTo(b['due'] as DateTime));
    final early = rows(state, 'history').where((h) => h['early'] == 1).toList();
    final counts = <String, int>{};
    for (final h in early) { final key = '${h['location_snapshot']} · ${h['part']}'; counts[key] = (counts[key] ?? 0) + 1; }
    return panel('Maintenance outlook', [
      const Text('Overdue and due in the next 30 days, for equipment you can access. Dates are based on recorded replacements and current intervals.'),
      if (unknown > 0) Text('$unknown compatible parts have no recorded replacement date; their due date is unknown.'),
      if (due.isEmpty) const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: Text('No known replacements due in the next 30 days.')),
      for (final item in due) ListTile(contentPadding: EdgeInsets.zero, leading: Icon((item['due'] as DateTime).isBefore(DateTime.now()) ? Icons.warning_amber_rounded : Icons.event_outlined), title: Text('${item['part']}'), subtitle: Text('${item['machine']}\nDue ${date(item['due'])}')),
      const Divider(),
      Text('${early.length} early replacements in the accessible recorded history.'),
      for (final entry in counts.entries.where((e) => e.value > 1)) Text('${entry.key}: ${entry.value} early replacements — consider a reliability review.'),
    ]);
  }
  Widget reportsPage() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [maintenancePlan(), ReportExporter(key: const ValueKey('report-exporter'), api: widget.api, role: state['user']['role'] as String)]);
  Widget auditLog() => purchasingAllowed ? RecordBrowser(key: const ValueKey('audit-browser'), api: widget.api, audit: true, parts: rows(state, 'parts')) : const Text('Lead or Administrator permission required.');
  Widget stockMovements() => purchasingAllowed ? RecordBrowser(key: const ValueKey('ledger-browser'), api: widget.api, audit: false, parts: rows(state, 'parts')) : const Text('Lead or Administrator permission required.');
  String alertFilter = 'Active';
  Future<void> acknowledgeAlert(int id) async {
    try { await widget.api.action('alert_ack', {'alert_id': id}); await refresh(); }
    catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(cleanError(e)))); }
  }
  bool alertVisible(Map<String, dynamic> a) => alertFilter == 'All' || (alertFilter == 'Resolved' ? a['resolved'] != null : a['resolved'] == null && (alertFilter != 'Unacknowledged' || a['acknowledged'] == 0));
  Widget alertsPanel() => panel('Persistent alerts', subtitle: 'Acknowledging marks an alert as seen for you. It stays active until the condition clears. Background checks require the configured worker to be running.', [
    SizedBox(width: 260, child: DropdownButtonFormField<String>(isExpanded: true, value: alertFilter, decoration: const InputDecoration(labelText: 'Alert status'), items: ['Active', 'Unacknowledged', 'Resolved', 'All'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(), onChanged: (v) => setState(() => alertFilter = v!))),
    const SizedBox(height: 12),
    if (!rows(state, 'alerts').any(alertVisible)) const EmptyState('No alerts match this status.', icon: Icons.notifications_off_outlined),
    for (final a in rows(state, 'alerts').where(alertVisible)) Card(color: a['resolved'] == null ? Colors.white : Palette.subtle, margin: const EdgeInsets.only(bottom: 10), child: ListTile(contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6), leading: Icon(a['resolved'] != null ? Icons.check_circle_outline : Icons.warning_amber_rounded, color: a['resolved'] != null ? Palette.okFg : Palette.warnFg), title: Text('${a['kind']} • ${a['resolved'] == null ? 'Active' : 'Resolved'}', style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text('${a['message']}\nOpened ${date(a['opened'])}${a['resolved'] == null ? '' : ' • Resolved ${date(a['resolved'])}'}'), trailing: a['resolved'] != null ? null : a['acknowledged'] == 1 ? const StatusPill('Seen', tone: Tone.neutral, icon: Icons.visibility_outlined) : TextButton(onPressed: () => acknowledgeAlert(a['id'] as int), child: const Text('Acknowledge')))),
  ]);
  Widget notifications() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [alertsPanel(), panel('Messages', subtitle: 'Email delivery is optional and must be enabled by your administrator. In-app notifications remain available here.', [if (rows(state, 'notifications').isEmpty) const EmptyState('No notifications.', icon: Icons.notifications_none), for (final n in rows(state, 'notifications')) ListTile(contentPadding: EdgeInsets.zero, leading: const CircleAvatar(radius: 18, backgroundColor: Palette.brandSoft, child: Icon(Icons.notifications_outlined, size: 18, color: Palette.brand)), title: Text(n['message'] as String), subtitle: Text(date(n['created'])))])]);
  static const navGroups = [('Daily work', [0, 1, 2, 3, 6]), ('Records & purchasing', [7, 4, 9, 8, 10]), ('Setup', [5])];
  bool visiblePage(int i) => ![5, 7, 8, 9].contains(i) || purchasingAllowed;
  int? badgeFor(int i) {
    final n = i == 3 ? rows(state, 'requests').where((r) => r['state'] == 'Pending').length : i == 6 ? rows(state, 'alerts').where((a) => a['resolved'] == null && a['acknowledged'] == 0).length : 0;
    return n > 0 ? n : null;
  }
  @override Widget build(BuildContext context) {
    final body = loading && state.isEmpty ? const Center(child: CircularProgressIndicator()) : error != null ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [Notice(error!, tone: Tone.danger), const SizedBox(height: 12), FilledButton.tonal(onPressed: refresh, child: const Text('Retry'))]))) : SingleChildScrollView(padding: EdgeInsets.all(compact ? 12 : 28), child: Align(alignment: Alignment.topCenter, child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 1180), child: [overview, equipment, inventory, approvals, history, administration, notifications, reorders, auditLog, stockMovements, reportsPage][page]())));
    final user = state['user'] as Map? ?? {};
    final nav = ListView(padding: const EdgeInsets.only(bottom: 16), children: [
      Padding(padding: const EdgeInsets.fromLTRB(20, 22, 20, 14), child: Row(children: [
        Container(padding: const EdgeInsets.all(7), decoration: BoxDecoration(color: Palette.brand, borderRadius: BorderRadius.circular(10)), child: const Icon(Icons.precision_manufacturing_outlined, color: Colors.white, size: 22)),
        const SizedBox(width: 12),
        const Flexible(child: Text('MachineCare', style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800, color: Palette.ink))),
      ])),
      for (final (label, items) in navGroups) if (items.any(visiblePage)) ...[
        Padding(padding: const EdgeInsets.fromLTRB(22, 14, 16, 6), child: Text(label.toUpperCase(), style: const TextStyle(fontSize: 11.5, letterSpacing: 1, fontWeight: FontWeight.w700, color: Palette.muted))),
        for (final i in items) if (visiblePage(i)) Padding(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 1), child: ListTile(dense: true, visualDensity: const VisualDensity(vertical: -1), selected: page == i, leading: Icon(icons[i], size: 22), title: Text(pages[i], style: TextStyle(fontSize: 15, fontWeight: page == i ? FontWeight.w700 : FontWeight.w500)), trailing: badgeFor(i) == null ? null : CountBadge(badgeFor(i)!, tone: i == 6 ? Tone.danger : Tone.warn), onTap: () { setState(() => page = i); if (MediaQuery.sizeOf(context).width < 900) Navigator.pop(context); })),
      ],
      const Divider(height: 32),
      Padding(padding: const EdgeInsets.symmetric(horizontal: 20), child: Row(children: [
        CircleAvatar(radius: 18, backgroundColor: Palette.brandSoft, child: Text('${user['username'] ?? '?'}'.substring(0, 1).toUpperCase(), style: const TextStyle(color: Palette.brand, fontWeight: FontWeight.w700))),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${user['username'] ?? ''}', overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.titleSmall), Text('${user['role'] ?? ''} · local workspace', overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.bodySmall)])),
      ])),
    ]);
    return LayoutBuilder(builder: (ctx, size) => Scaffold(appBar: AppBar(title: Text(pages[page]), actions: [if (size.maxWidth >= 700) Flexible(child: Padding(padding: const EdgeInsets.only(right: 8), child: Text('${state['user']?['username'] ?? ''} · ${state['user']?['role'] ?? ''}', overflow: TextOverflow.ellipsis, style: const TextStyle(color: Palette.muted, fontWeight: FontWeight.w600)))), IconButton(tooltip: 'Refresh', onPressed: loading ? null : refresh, icon: const Icon(Icons.refresh)), IconButton(tooltip: 'Change password', onPressed: () async { if (await changePassword(context, widget.api) && context.mounted) Navigator.pop(context); }, icon: const Icon(Icons.password)), IconButton(tooltip: 'Sign out', onPressed: () async { try { await widget.api.action('logout', {}); } finally { widget.api.token = null; if (context.mounted) Navigator.pop(context); } }, icon: const Icon(Icons.logout)), const SizedBox(width: 8)]), drawer: size.maxWidth < 900 ? Drawer(child: nav) : null, body: Column(children: [if (loading) const LinearProgressIndicator(minHeight: 3), Expanded(child: Row(children: [if (size.maxWidth >= 900) Container(width: 250, decoration: const BoxDecoration(color: Colors.white, border: Border(right: BorderSide(color: Palette.border))), child: nav), Expanded(child: body)]))])));
  }
}

class SystemStatus extends StatefulWidget {
  final Api api;
  const SystemStatus({super.key, required this.api});
  @override State<SystemStatus> createState() => _SystemStatusState();
}
class _SystemStatusState extends State<SystemStatus> {
  Map<String, dynamic>? data;
  String? error;
  bool busy = false;
  Future<void> load() async {
    if (busy) return;
    setState(() { busy = true; error = null; });
    try { final result = await widget.api.action('system_status', {}); if (mounted) setState(() => data = result); }
    catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text('Background services', style: Theme.of(context).textTheme.titleLarge),
    const Text('Check the last successful background check, scheduled backup and email queue. Configuration is managed on the backend computer.'),
    TextButton.icon(onPressed: busy ? null : load, icon: const Icon(Icons.refresh), label: const Text('Check service status')),
    if (busy) const LinearProgressIndicator(),
    if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
    if (data != null && rows(data!, 'jobs').isEmpty) const Text('No worker activity recorded. Background services have not been started.'),
    if (data != null) ...[
      for (final job in rows(data!, 'jobs')) Text('${job['name']}: ${job['last_success'] == null ? 'No successful run' : DateTime.fromMillisecondsSinceEpoch(((job['last_success'] as num) * 1000).round()).toLocal()}${job['last_error'] == null ? '' : ' — ${job['last_error']}'}'),
      for (final queue in rows(data!, 'email_queue')) Text('Email ${queue['state']}: ${queue['count']}'),
    ],
  ])));
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
    if (busy) return;
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
        if (error != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(error!, style: const TextStyle(color: Color(0xffb3261e)))),
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
    if (busy) return;
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
      if (error != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(error!, style: const TextStyle(color: Color(0xffb3261e)))),
    ]))),
    actions: [TextButton(onPressed: busy ? null : () => Navigator.pop(context), child: const Text('Cancel')), FilledButton(onPressed: busy ? null : save, child: Text(busy ? 'Saving…' : creating ? 'Add part' : 'Save details'))],
  );
}

class ReorderRequestEditor extends StatefulWidget {
  final List<Map<String, dynamic>> parts;
  final int? initialPartId;
  final Future<void> Function(Map<String, dynamic>) onSave;
  const ReorderRequestEditor({super.key, required this.parts, this.initialPartId, required this.onSave});
  @override State<ReorderRequestEditor> createState() => _ReorderRequestEditorState();
}

/// Read-only record browser. Each page uses a stable server ID cursor.
class RecordBrowser extends StatefulWidget {
  final Api api;
  final bool audit;
  final List<Map<String, dynamic>> parts;
  final void Function(String, String)? onDownload;
  const RecordBrowser({super.key, required this.api, required this.audit, required this.parts, this.onDownload});
  @override State<RecordBrowser> createState() => _RecordBrowserState();
}
class _RecordBrowserState extends State<RecordBrowser> {
  final search = TextEditingController();
  final event = TextEditingController();
  List<Map<String, dynamic>> items = [];
  int? cursor, partId;
  DateTime? from, to;
  String direction = 'All';
  bool busy = false, more = false, filtersChanged = false;
  String? error;
  @override void initState() { super.initState(); load(); }
  @override void dispose() { search.dispose(); event.dispose(); super.dispose(); }
  String day(DateTime d) => '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  String time(dynamic value) => DateTime.tryParse('$value')?.toLocal().toString() ?? '$value';
  Future<void> chooseDate(bool start) async {
    final chosen = await showDatePicker(context: context, initialDate: (start ? from : to) ?? DateTime.now(), firstDate: DateTime(2000), lastDate: DateTime(2100));
    if (!mounted || chosen == null) return;
    setState(() { if (start) { from = chosen; } else { to = chosen; } filtersChanged = true; });
  }
  Map<String, dynamic> filters() => {'search': search.text.trim(), if (from != null) 'from_date': day(from!), if (to != null) 'to_date': day(to!), if (widget.audit) 'event': event.text.trim(), if (!widget.audit) ...{'direction': direction, if (partId != null) 'part_id': partId}};
  Future<void> export() async {
    if (busy) return;
    setState(() { busy = true; error = null; });
    try {
      final result = await widget.api.action('report_export', {...filters(), 'report': widget.audit ? 'audit' : 'stock_movements'});
      if (!mounted) return;
      (widget.onDownload ?? downloadCsv)(result['filename'] as String, result['csv'] as String);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Download requested: ${result['row_count']} matching records. Check Chrome downloads.')));
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> load({bool next = false}) async {
    if (busy) return;
    setState(() { busy = true; error = null; });
    try {
      final result = await widget.api.action(widget.audit ? 'audit_list' : 'ledger_list', {
        ...filters(), 'limit': 50, if (next && cursor != null) 'cursor': cursor,
      });
      if (!mounted) return;
      setState(() {
        final page = rows(result, 'records');
        items = next ? [...items, ...page] : page;
        cursor = result['next_cursor'] as int?; more = result['has_more'] == true; filtersChanged = false;
      });
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  void clear() {
    setState(() { search.clear(); event.clear(); from = null; to = null; partId = null; direction = 'All'; filtersChanged = true; });
    load();
  }
  @override Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Text(widget.audit ? 'Audit log' : 'Stock movement history', style: Theme.of(context).textTheme.headlineSmall),
    const SizedBox(height: 12),
    Text(widget.audit ? 'Recorded actions and their details. Sensitive credential fields are redacted. Includes authentication events and account changes. Background check status is available to your administrator.' : 'Recorded physical stock changes. Reservations are shown in Inventory and do not create stock movements. Balance after is calculated from all recorded movements for that SKU.'),
    const SizedBox(height: 16),
    TextField(controller: search, enabled: !busy, decoration: InputDecoration(labelText: widget.audit ? 'Search action or actor' : 'Search part, SKU, reason or actor', prefixIcon: const Icon(Icons.search)), onChanged: (_) => setState(() => filtersChanged = true), onSubmitted: (_) => load()),
    const SizedBox(height: 14),
    if (widget.audit) TextField(controller: event, enabled: !busy, decoration: const InputDecoration(labelText: 'Exact action (optional)', hintText: 'For example: reorder_receive or edit_part'), onChanged: (_) => setState(() => filtersChanged = true)),
    if (!widget.audit) Wrap(spacing: 16, runSpacing: 14, children: [
      SizedBox(width: 280, child: DropdownButtonFormField<int>(value: partId, isExpanded: true, decoration: const InputDecoration(labelText: 'Part'), items: [const DropdownMenuItem<int>(value: null, child: Text('All parts')), ...widget.parts.map((p) => DropdownMenuItem<int>(value: p['id'] as int, child: Text('${p['name']} · ${p['sku']}', overflow: TextOverflow.ellipsis)))], onChanged: busy ? null : (v) => setState(() { partId = v; filtersChanged = true; }))),
      SizedBox(width: 200, child: DropdownButtonFormField<String>(value: direction, decoration: const InputDecoration(labelText: 'Direction'), items: ['All', 'In', 'Out'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(), onChanged: busy ? null : (v) => setState(() { direction = v!; filtersChanged = true; }))),
    ]),
    const SizedBox(height: 12),
    Wrap(spacing: 12, runSpacing: 8, children: [
      OutlinedButton(onPressed: busy ? null : () => chooseDate(true), child: Text(from == null ? 'From date (UTC)' : 'From ${day(from!)}')),
      OutlinedButton(onPressed: busy ? null : () => chooseDate(false), child: Text(to == null ? 'To date (UTC)' : 'To ${day(to!)}')),
      FilledButton(onPressed: busy ? null : () => load(), child: const Text('Apply / refresh records')),
      TextButton(onPressed: busy ? null : clear, child: const Text('Clear filters')),
      OutlinedButton.icon(onPressed: busy ? null : export, icon: const Icon(Icons.download), label: const Text('Export matching CSV')),
    ]),
    if (busy) const LinearProgressIndicator(),
    if (error != null) Padding(padding: const EdgeInsets.all(12), child: Text(error!, style: const TextStyle(color: Color(0xffb3261e)))),
    Text('${items.length} records loaded${more ? ' • more available' : ''}. Filters apply when you select Apply / refresh records. CSV export uses the current filter fields and includes all matching rows, up to 10,000.'),
    if (!busy && items.isEmpty && error == null) const Padding(padding: EdgeInsets.all(20), child: Text('No records match these filters.')),
    for (final r in items) Card(child: widget.audit ? ExpansionTile(
      key: ValueKey('audit:${r['id']}'), title: Text('#${r['id']} · ${r['action']}'), subtitle: Text('${r['actor']} • ${time(r['created'])}'),
      children: [Padding(padding: const EdgeInsets.all(16), child: Align(alignment: Alignment.centerLeft, child: SelectableText(const JsonEncoder.withIndent('  ').convert(r['detail']))))],
    ) : ListTile(key: ValueKey('movement:${r['id']}'), title: Text('${r['part']} · ${r['sku']} · ${(r['delta'] as num) > 0 ? '+' : ''}${r['delta']}'), subtitle: Text('${r['reason']}\n${r['actor']} • ${time(r['created'])}'), trailing: Text('Balance after\n${r['balance_after']}'))),
    if (more) Padding(padding: const EdgeInsets.all(16), child: OutlinedButton(onPressed: busy || filtersChanged ? null : () => load(next: true), child: const Text('Load more'))),
  ]);
}
class _ReorderRequestEditorState extends State<ReorderRequestEditor> {
  late int partId;
  final quantity = TextEditingController(), reason = TextEditingController();
  bool busy = false; String? error;
  Map<String, dynamic> get part => widget.parts.firstWhere((p) => p['id'] == partId);
  @override void initState() { super.initState(); partId = widget.initialPartId ?? (widget.parts.first['id'] as int); resetSuggestion(); }
  void resetSuggestion() { final suggested = part['suggested_order_quantity'] as int? ?? 0; quantity.text = suggested > 0 ? '$suggested' : '1'; }
  @override void dispose() { quantity.dispose(); reason.dispose(); super.dispose(); }
  Future<void> save() async {
    if (busy) return;
    setState(() { busy = true; error = null; });
    try {
      final amount = int.tryParse(quantity.text.trim());
      if (amount == null || amount < 1) throw Exception('Quantity must be a positive whole number.');
      if (reason.text.trim().isEmpty) throw Exception('A reorder reason is required.');
      await widget.onSave({'part_id': partId, 'quantity': amount, 'reason': reason.text.trim()});
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => AlertDialog(title: const Text('Request reorder'), content: SizedBox(width: 520, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
    DropdownButtonFormField<int>(value: partId, isExpanded: true, decoration: const InputDecoration(labelText: 'Part'), items: widget.parts.map((p) => DropdownMenuItem<int>(value: p['id'] as int, child: Text('${p['name']} · ${p['sku']}', overflow: TextOverflow.ellipsis))).toList(), onChanged: busy ? null : (id) => setState(() { partId = id!; resetSuggestion(); })),
    const SizedBox(height: 14), Text('Stock ${part['stock']} • Available ${part['available_quantity'] ?? part['stock']} • Reserved ${part['reserved_quantity'] ?? 0} • Target ${part['target']} • Approved/ordered outstanding ${part['outstanding_order_quantity'] ?? 0} • Pending requests ${part['pending_reorder_quantity'] ?? 0}'),
    Text('Suggested quantity: ${part['suggested_order_quantity'] ?? 0}. You can request a different quantity with a reason.'),
    const SizedBox(height: 14), TextField(controller: quantity, enabled: !busy, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Requested quantity')),
    const SizedBox(height: 14), TextField(controller: reason, enabled: !busy, decoration: const InputDecoration(labelText: 'Reorder reason')),
    const SizedBox(height: 14), const Text('Lead requests are approved immediately; Administrator requests need a separate Lead or Administrator’s approval. Physical deliveries add stock after ordering.'),
    if (error != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(error!, style: const TextStyle(color: Color(0xffb3261e)))),
  ]))), actions: [TextButton(onPressed: busy ? null : () => Navigator.pop(context), child: const Text('Cancel')), FilledButton(onPressed: busy ? null : save, child: Text(busy ? 'Submitting…' : 'Submit reorder'))]);
}

class ReportExporter extends StatefulWidget {
  final Api api;
  final String role;
  final void Function(String, String)? onDownload;
  const ReportExporter({super.key, required this.api, required this.role, this.onDownload});
  @override State<ReportExporter> createState() => _ReportExporterState();
}
class _ReportExporterState extends State<ReportExporter> {
  final search = TextEditingController();
  String report = 'maintenance';
  DateTime? from, to;
  bool busy = false;
  String? error, message;
  List<String> get choices => ['maintenance', 'inventory', if (['Lead', 'Administrator'].contains(widget.role)) 'reorders'];
  String day(DateTime d) => '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  @override void dispose() { search.dispose(); super.dispose(); }
  Future<void> date(bool start) async {
    final picked = await showDatePicker(context: context, initialDate: (start ? from : to) ?? DateTime.now(), firstDate: DateTime(2000), lastDate: DateTime(2100));
    if (mounted && picked != null) setState(() { if (start) { from = picked; } else { to = picked; } });
  }
  Future<void> export() async {
    setState(() { busy = true; error = null; message = null; });
    try {
      final result = await widget.api.action('report_export', {'report': report, 'search': search.text.trim(), if (report != 'inventory' && from != null) 'from_date': day(from!), if (report != 'inventory' && to != null) 'to_date': day(to!)});
      if (!mounted) return;
      (widget.onDownload ?? downloadCsv)(result['filename'] as String, result['csv'] as String);
      setState(() => message = 'Download requested: ${result['row_count']} rows. Check Chrome downloads.');
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => Card(child: Padding(padding: EdgeInsets.all(MediaQuery.sizeOf(context).width < 600 ? 16 : 22), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text('CSV reports', style: Theme.of(context).textTheme.titleLarge),
    const SizedBox(height: 14),
    const Text('Download maintenance history, current inventory or reorder history. Stock movement and audit exports are available on their respective screens. Exports contain all matches, up to 10,000 rows; narrow filters if the limit is exceeded.', style: TextStyle(color: Palette.muted)),
    const SizedBox(height: 18),
    DropdownButtonFormField<String>(isExpanded: true, value: report, decoration: const InputDecoration(labelText: 'Report'), items: choices.map((r) => DropdownMenuItem(value: r, child: Text(r == 'maintenance' ? 'Maintenance history' : r == 'inventory' ? 'Current inventory' : 'Reorder history'))).toList(), onChanged: busy ? null : (r) => setState(() { report = r!; error = null; message = null; })),
    const SizedBox(height: 14),
    TextField(controller: search, enabled: !busy, decoration: const InputDecoration(labelText: 'Search report records', hintText: 'Part, SKU, location, person or reason as applicable')),
    const SizedBox(height: 14),
    if (report != 'inventory') Wrap(spacing: 12, runSpacing: 8, children: [OutlinedButton(onPressed: busy ? null : () => date(true), child: Text(from == null ? 'From date (UTC)' : 'From ${day(from!)}')), OutlinedButton(onPressed: busy ? null : () => date(false), child: Text(to == null ? 'To date (UTC)' : 'To ${day(to!)}'))]),
    if (report == 'inventory') const Text('Inventory is a current snapshot; date filters do not apply.'),
    const SizedBox(height: 14),
    Wrap(spacing: 12, runSpacing: 8, children: [FilledButton.icon(onPressed: busy ? null : export, icon: const Icon(Icons.download), label: Text(busy ? 'Preparing…' : 'Download CSV')), TextButton(onPressed: busy ? null : () => setState(() { search.clear(); from = null; to = null; error = null; message = null; }), child: const Text('Clear filters'))]),
    if (error != null) Text(error!, style: const TextStyle(color: Color(0xffb3261e))),
    if (message != null) Text(message!),
  ])));
}
