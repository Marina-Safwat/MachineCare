import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/api.dart';
import 'package:machinecare/workspace.dart';

class FakeApi extends Api {
  final String role;
  bool failAcknowledgement = false;
  final alerts = <Map<String, dynamic>>[
    {'id': 1, 'kind': 'Low stock', 'message': 'Active shortage', 'opened': '2026-10-09T10:00:00+00:00', 'resolved': null, 'acknowledged': 0},
    {'id': 2, 'kind': 'Low stock', 'message': 'Resolved shortage', 'opened': '2026-10-08T10:00:00+00:00', 'resolved': '2026-10-09T10:00:00+00:00', 'acknowledged': 0},
  ];
  FakeApi({this.role = 'Administrator'});
  @override Future<Map<String, dynamic>> call(String path, [Map<String, dynamic>? data]) async {
    if (path == '/actions/alert_ack') {
      if (failAcknowledgement) throw Exception('Acknowledgement unavailable');
      alerts.firstWhere((a) => a['id'] == data!['alert_id'])['acknowledged'] = 1;
      return {};
    }
    return {
      'user': {'id': 1, 'username': 'Demo', 'role': role},
      'machines': [], 'requests': [], 'history': [], 'buildings': [], 'lines': [], 'types': [], 'users': [], 'notifications': [], 'deliveries': [],
      'parts': [{'id': 1, 'name': 'Seal', 'sku': 'SEAL', 'stock': 12, 'reserved_quantity': 7, 'available_quantity': 5, 'reservation_shortfall': 0, 'bin': 'A1', 'threshold': 5, 'target': 20, 'interval_days': 90, 'cost': 2.0, 'supplier': '', 'suggested_order_quantity': 15}],
      'alerts': alerts.map((a) => Map<String, dynamic>.from(a)).toList(),
      'reorders': [{'id': 1, 'part': 'Seal', 'sku': 'SEAL', 'state': 'Approved', 'quantity': 10, 'received_quantity': 0, 'requested_by': 1, 'requester': 'Demo', 'created': '2026-10-09T10:00:00+00:00', 'supplier_snapshot': '', 'supplier_number_snapshot': '', 'unit_cost_snapshot': 2.0, 'reason': 'Replenish', 'review_comment': 'Lead request: approval not required', 'revision': 0}],
    };
  }
}
Future<void> launch(WidgetTester tester, FakeApi api) async {
  tester.view.physicalSize = const Size(1280, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(MaterialApp(home: Workspace(api: api)));
  await tester.pumpAndSettle();
}
void main() {
  testWidgets('Inventory displays physical, reserved and available balances', (tester) async {
    await launch(tester, FakeApi());
    await tester.tap(find.text('Inventory')); await tester.pumpAndSettle();
    expect(find.text('Physical stock: 12 • Reserved: 7 • Available: 5 • Bin: A1'), findsOneWidget);
    expect(find.text('LOW STOCK • reorder planning required'), findsOneWidget);
  });
  testWidgets('Acknowledgement keeps active condition visible and filters resolved history', (tester) async {
    await launch(tester, FakeApi());
    await tester.tap(find.text('Notifications')); await tester.pumpAndSettle();
    expect(find.textContaining('Active shortage'), findsOneWidget);
    expect(find.textContaining('Resolved shortage'), findsNothing);
    await tester.tap(find.text('Acknowledge')); await tester.pumpAndSettle();
    expect(find.text('Seen'), findsOneWidget);
    expect(find.textContaining('Active shortage'), findsOneWidget);
    await tester.tap(find.byType(DropdownButtonFormField<String>)); await tester.pumpAndSettle();
    await tester.tap(find.text('Resolved').last); await tester.pumpAndSettle();
    expect(find.textContaining('Resolved shortage'), findsOneWidget);
    expect(find.textContaining('Active shortage'), findsNothing);
    expect(find.text('Acknowledge'), findsNothing);
  });
  testWidgets('Acknowledgement failure stays visible without marking seen', (tester) async {
    final api = FakeApi()..failAcknowledgement = true;
    await launch(tester, api);
    await tester.tap(find.text('Notifications')); await tester.pumpAndSettle();
    await tester.tap(find.text('Acknowledge')); await tester.pump();
    expect(find.text('Acknowledgement unavailable'), findsOneWidget);
    expect(find.text('Seen'), findsNothing);
    expect(find.text('Acknowledge'), findsOneWidget);
  });
  testWidgets('Lead reorder shows bypass confirmation and cannot receive or order', (tester) async {
    await launch(tester, FakeApi(role: 'Lead'));
    await tester.tap(find.text('Reorders')); await tester.pumpAndSettle();
    expect(find.text('Review: Lead request: approval not required'), findsOneWidget);
    expect(find.text('Approve order'), findsNothing);
    expect(find.text('Mark ordered'), findsNothing);
    expect(find.text('Receive delivery'), findsNothing);
    expect(find.text('Cancel remaining'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
