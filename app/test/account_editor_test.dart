import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';

Widget editorHost(AccountEditor editor) => MaterialApp(home: Builder(builder: (context) => Scaffold(body: TextButton(
  onPressed: () { showDialog<bool>(context: context, builder: (_) => editor); },
  child: const Text('Open editor'),
))));

void main() {
  testWidgets('Editing an existing account sends its selected access and assigned lead', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(editorHost(AccountEditor(
      user: {'id': 3, 'username': 'Tech', 'role': 'Technician', 'lead_id': 2, 'building_ids': [1]},
      users: [{'id': 2, 'username': 'Lead', 'role': 'Lead', 'active': 1}],
      buildings: [{'id': 1, 'code': 'B01', 'name': 'Building 1'}, {'id': 3, 'code': 'B03', 'name': 'Building 3'}],
      onSave: (data) async { saved = data; },
    )));
    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('B03 · Building 3'));
    await tester.tap(find.text('B03 · Building 3'));
    await tester.pump();
    await tester.tap(find.text('Save account'));
    await tester.pumpAndSettle();
    expect(saved, {'user_id': 3, 'role': 'Technician', 'lead_id': 2, 'building_ids': [1, 3], 'line_ids': []});
    expect(tester.takeException(), isNull);
  });
  testWidgets('Rejected account edit preserves selections and displays the server error', (tester) async {
    await tester.pumpWidget(editorHost(AccountEditor(
      user: {'id': 3, 'username': 'Tech', 'role': 'Technician', 'lead_id': 2, 'building_ids': [1]},
      users: [{'id': 2, 'username': 'Lead', 'role': 'Lead', 'active': 1}],
      buildings: [{'id': 1, 'code': 'B01', 'name': 'Building 1'}],
      onSave: (_) async { throw Exception('Pending requests need an assigned lead.'); },
    )));
    await tester.tap(find.text('Open editor'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save account'));
    await tester.pumpAndSettle();
    expect(find.text('Pending requests need an assigned lead.'), findsOneWidget);
    expect(tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value, isTrue);
    expect(find.text('Save account'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
