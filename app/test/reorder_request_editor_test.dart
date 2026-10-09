import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';

const parts = <Map<String, dynamic>>[
  {'id': 1, 'name': 'Seal kit', 'sku': 'SEAL-1', 'stock': 12, 'target': 20,
   'suggested_order_quantity': 8, 'outstanding_order_quantity': 0, 'pending_reorder_quantity': 0},
];
Widget host(Future<void> Function(Map<String, dynamic>) save) => MaterialApp(home: Builder(builder: (context) => Scaffold(body: TextButton(
  onPressed: () { showDialog<bool>(context: context, builder: (_) => ReorderRequestEditor(parts: parts, onSave: save)); },
  child: const Text('Open reorder'),
))));
Future<void> open(WidgetTester tester) async {
  await tester.tap(find.text('Open reorder')); await tester.pumpAndSettle();
}
Future<void> fill(WidgetTester tester, String label, String value) async {
  final field = find.widgetWithText(TextField, label);
  await tester.ensureVisible(field); await tester.enterText(field, value); await tester.pump();
}
void main() {
  testWidgets('Suggestion is editable and submit sends selected part and reason', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(host((data) async { saved = data; })); await open(tester);
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Requested quantity')).controller!.text, '8');
    await fill(tester, 'Requested quantity', '10'); await fill(tester, 'Reorder reason', 'Upcoming service');
    await tester.tap(find.text('Submit reorder')); await tester.pumpAndSettle();
    expect(saved, {'part_id': 1, 'quantity': 10, 'reason': 'Upcoming service'});
    expect(tester.takeException(), isNull);
  });
  testWidgets('Invalid quantity and empty reason never call the server', (tester) async {
    var saves = 0;
    await tester.pumpWidget(host((_) async { saves++; })); await open(tester);
    await fill(tester, 'Requested quantity', '0');
    await tester.tap(find.text('Submit reorder')); await tester.pumpAndSettle();
    expect(saves, 0); expect(find.text('Quantity must be a positive whole number.'), findsOneWidget);
    await fill(tester, 'Requested quantity', '8');
    await tester.tap(find.text('Submit reorder')); await tester.pumpAndSettle();
    expect(saves, 0); expect(find.text('A reorder reason is required.'), findsOneWidget);
  });
  testWidgets('Server rejection preserves the request for correction', (tester) async {
    await tester.pumpWidget(host((_) async { throw Exception('Request rejected'); })); await open(tester);
    await fill(tester, 'Reorder reason', 'Upcoming service');
    await tester.tap(find.text('Submit reorder')); await tester.pumpAndSettle();
    expect(find.text('Request rejected'), findsOneWidget);
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Reorder reason')).controller!.text, 'Upcoming service');
    expect(tester.takeException(), isNull);
  });
  testWidgets('Cancel and reopen do not reuse disposed controllers', (tester) async {
    await tester.pumpWidget(host((_) async {}));
    for (var i = 0; i < 2; i++) {
      await open(tester); await fill(tester, 'Reorder reason', 'Unsaved');
      await tester.tap(find.text('Cancel')); await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
  });
}
