import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';

const buildings = [{'id': 1, 'code': 'B01', 'name': 'Building 1'}];
const lines = [{'id': 1, 'building_id': 1, 'code': 'L01'}, {'id': 2, 'building_id': 1, 'code': 'L02'}];
Widget host(AccountEditor editor) => MaterialApp(home: Builder(builder: (context) => Scaffold(body: TextButton(
  onPressed: () { showDialog<bool>(context: context, builder: (_) => editor); }, child: const Text('Open editor'),
))));

void main() {
  testWidgets('Selecting one line sends no whole-building grant', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(host(AccountEditor(
      user: {'id': 3, 'username': 'Tech', 'role': 'Technician', 'lead_id': null, 'building_ids': [], 'line_ids': []},
      users: const [], buildings: buildings, lines: lines,
      onSave: (data) async { saved = data; },
    )));
    await tester.tap(find.text('Open editor')); await tester.pumpAndSettle();
    final first = find.byKey(const ValueKey('line-access:1'));
    await tester.ensureVisible(first); await tester.tap(first); await tester.pump();
    expect(tester.widget<CheckboxListTile>(first).value, isTrue);
    expect(tester.widget<CheckboxListTile>(find.byKey(const ValueKey('line-access:2'))).value, isFalse);
    await tester.tap(find.text('Save account')); await tester.pumpAndSettle();
    expect(saved?['building_ids'], isEmpty);
    expect(saved?['line_ids'], [1]);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Whole-building access includes lines without inventing explicit grants', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(host(AccountEditor(
      user: {'id': 3, 'username': 'Lead', 'role': 'Lead', 'building_ids': [], 'line_ids': []},
      users: const [], buildings: buildings, lines: lines,
      onSave: (data) async { saved = data; },
    )));
    await tester.tap(find.text('Open editor')); await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('B01 · Building 1'));
    await tester.tap(find.text('B01 · Building 1')); await tester.pump();
    for (final id in [1, 2]) {
      final tile = tester.widget<CheckboxListTile>(find.byKey(ValueKey('line-access:$id')));
      expect(tile.value, isTrue); expect(tile.onChanged, isNull);
    }
    await tester.tap(find.text('Save account')); await tester.pumpAndSettle();
    expect(saved?['building_ids'], [1]); expect(saved?['line_ids'], isEmpty);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Account creation sends credentials and an individual line assignment', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(host(AccountEditor(
      creating: true, user: const {'role': 'Technician', 'building_ids': [], 'line_ids': []},
      users: const [], buildings: buildings, lines: lines,
      onSave: (data) async { saved = data; },
    )));
    await tester.tap(find.text('Open editor')); await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Username'), 'new-tech');
    await tester.enterText(find.widgetWithText(TextField, 'Temporary password (12+ characters)'), 'Temporary-password!');
    final second = find.byKey(const ValueKey('line-access:2'));
    await tester.ensureVisible(second); await tester.tap(second); await tester.pump();
    await tester.tap(find.text('Create account')); await tester.pumpAndSettle();
    expect(saved?['username'], 'new-tech'); expect(saved?['line_ids'], [2]);
    expect(saved?['building_ids'], isEmpty); expect(saved?.containsKey('user_id'), isFalse);
    expect(tester.takeException(), isNull);
  });
}
