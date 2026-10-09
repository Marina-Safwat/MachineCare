import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/api.dart';
import 'package:machinecare/workspace.dart';

class RecordApi extends Api {
  final calls = <Map<String, dynamic>>[];
  bool fail = false;
  @override Future<Map<String, dynamic>> action(String name, Map<String, dynamic> data) async {
    calls.add({'action': name, ...data});
    if (fail) throw Exception('Records unavailable');
    if (data['search'] == 'missing') return {'records': [], 'has_more': false, 'next_cursor': null};
    if (name == 'audit_list') return {
      'records': [{'id': 3, 'action': 'reorder_receive', 'actor': 'Lead A', 'created': '2026-10-09T10:00:00+00:00', 'detail': {'quantity': 4, 'password': '[redacted]'}}],
      'has_more': false, 'next_cursor': null,
    };
    final next = data['cursor'] != null;
    return {
      'records': [{'id': next ? 1 : 2, 'part': 'Seal', 'sku': 'SEAL', 'delta': next ? 12 : -2, 'reason': next ? 'Opening balance' : 'Count correction', 'actor': next ? 'System' : 'Lead A', 'created': '2026-10-09T10:00:00+00:00', 'balance_after': next ? 12 : 10}],
      'has_more': !next, 'next_cursor': next ? null : 2,
    };
  }
}
Future<void> launch(WidgetTester tester, RecordApi api, {bool audit = false}) async {
  tester.view.physicalSize = const Size(1200, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: SingleChildScrollView(child: RecordBrowser(api: api, audit: audit, parts: const [{'id': 1, 'name': 'Seal', 'sku': 'SEAL'}])))));
  await tester.pumpAndSettle();
}
void main() {
  testWidgets('Movement shows signed change, actor and balance after', (tester) async {
    await launch(tester, RecordApi());
    expect(find.text('Seal · SEAL · -2'), findsOneWidget);
    expect(find.text('Balance after\n10'), findsOneWidget);
    expect(find.textContaining('Lead A'), findsOneWidget);
  });
  testWidgets('Load more uses cursor; changed filters require apply and reset paging', (tester) async {
    final api = RecordApi(); await launch(tester, api);
    await tester.tap(find.text('Load more')); await tester.pumpAndSettle();
    expect(api.calls.last['cursor'], 2);
    expect(find.text('Seal · SEAL · +12'), findsOneWidget);
    expect(find.text('Seal · SEAL · -2'), findsOneWidget);
    await tester.tap(find.text('Apply / refresh records')); await tester.pumpAndSettle();
    final field = find.widgetWithText(TextField, 'Search part, SKU, reason or actor');
    await tester.enterText(field, 'missing'); await tester.pump();
    expect(tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Load more')).onPressed, isNull);
    await tester.tap(find.text('Apply / refresh records')); await tester.pumpAndSettle();
    expect(api.calls.last.containsKey('cursor'), isFalse);
    expect(find.text('No records match these filters.'), findsOneWidget);
    await tester.tap(find.text('Clear filters')); await tester.pumpAndSettle();
    expect(api.calls.last['search'], ''); expect(find.text('Seal · SEAL · -2'), findsOneWidget);
  });
  testWidgets('Audit entry expands readable redacted details', (tester) async {
    final api = RecordApi(); await launch(tester, api, audit: true);
    expect(api.calls.last['action'], 'audit_list');
    await tester.tap(find.text('#3 · reorder_receive')); await tester.pumpAndSettle();
    expect(find.textContaining('"quantity": 4'), findsOneWidget);
    expect(find.textContaining('[redacted]'), findsOneWidget);
  });
  testWidgets('Failed refresh keeps records and can be retried', (tester) async {
    final api = RecordApi(); await launch(tester, api);
    api.fail = true;
    await tester.tap(find.text('Apply / refresh records')); await tester.pumpAndSettle();
    expect(find.text('Records unavailable'), findsOneWidget);
    expect(find.text('Seal · SEAL · -2'), findsOneWidget);
    api.fail = false;
    await tester.tap(find.text('Apply / refresh records')); await tester.pumpAndSettle();
    expect(find.text('Records unavailable'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
