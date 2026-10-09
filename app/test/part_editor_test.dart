import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';

const samplePart = <String, dynamic>{
  'id': 1, 'name': 'Seal kit', 'sku': 'SEAL-1', 'bin': 'A12',
  'supplier': 'Supplier', 'supplier_number': 'SUP-1', 'cost': 24.5,
  'stock': 12, 'threshold': 5, 'target': 20, 'lead_days': 3,
  'interval_days': 90, 'type_ids': [1], 'revision': 4,
};
const types = [{'id': 1, 'name': 'DIMM Press'}, {'id': 2, 'name': 'ACOS Station'}];
Widget host(Future<void> Function(Map<String, dynamic>) save) => MaterialApp(home: Builder(builder: (context) => Scaffold(body: TextButton(
  onPressed: () { showDialog<bool>(context: context, builder: (_) => PartEditor(part: samplePart, types: types, onSave: save)); },
  child: const Text('Edit part'),
))));
Future<void> fill(WidgetTester tester, String label, String value) async {
  final field = find.widgetWithText(TextField, label);
  await tester.ensureVisible(field);
  await tester.enterText(field, value);
  await tester.pump();
}
void main() {
  testWidgets('Part metadata save carries compatibility/revision but never stock', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(host((data) async { saved = data; }));
    await tester.tap(find.text('Edit part')); await tester.pumpAndSettle();
    await fill(tester, 'Part name', 'New seal name');
    final type = find.byKey(const ValueKey('part-type:2'));
    await tester.ensureVisible(type); await tester.tap(type); await tester.pump();
    await fill(tester, 'Change reason (required)', 'Supplier corrected');
    await tester.tap(find.text('Save details')); await tester.pumpAndSettle();
    expect(saved?['name'], 'New seal name'); expect(saved?['revision'], 4);
    expect(saved?['type_ids'], [1, 2]); expect(saved?.containsKey('stock'), isFalse);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Server error preserves the edited name and reason', (tester) async {
    await tester.pumpWidget(host((_) async { throw Exception('SKU already exists. Choose a unique SKU.'); }));
    await tester.tap(find.text('Edit part')); await tester.pumpAndSettle();
    await fill(tester, 'Part name', 'Unsaved name');
    await fill(tester, 'Change reason (required)', 'Correct SKU');
    await tester.tap(find.text('Save details')); await tester.pumpAndSettle();
    expect(find.text('SKU already exists. Choose a unique SKU.'), findsOneWidget);
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Part name')).controller!.text, 'Unsaved name');
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Change reason (required)')).controller!.text, 'Correct SKU');
    expect(tester.takeException(), isNull);
  });
  testWidgets('Missing change reason does not send a metadata update', (tester) async {
    var saves = 0;
    await tester.pumpWidget(host((_) async { saves++; }));
    await tester.tap(find.text('Edit part')); await tester.pumpAndSettle();
    await tester.tap(find.text('Save details')); await tester.pumpAndSettle();
    expect(saves, 0); expect(find.text('Change reason is required.'), findsOneWidget);
  });
  testWidgets('Cancelling and reopening the part editor creates live controllers', (tester) async {
    await tester.pumpWidget(host((_) async {}));
    for (var i = 0; i < 2; i++) {
      await tester.tap(find.text('Edit part')); await tester.pumpAndSettle();
      await fill(tester, 'Part name', 'Unsaved');
      await tester.tap(find.text('Cancel')); await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
  });
}
