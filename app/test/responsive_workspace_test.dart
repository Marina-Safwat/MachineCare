import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';
import 'package:machinecare/design.dart';
import 'reservations_alerts_test.dart' show FakeApi;
import '../tool/visual_preview.dart' show PreviewApi;

void main() {
  for (final width in [390.0, 768.0, 1440.0]) {
    for (final role in ['Administrator', 'Lead', 'Technician']) {
      testWidgets('$role pages fit width $width', (tester) async {
        tester.view.physicalSize = Size(width, 900); tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
        final api = FakeApi(role: role);
        api.requests.add({'id': 10, 'part': 'Seal with a longer descriptive name', 'machine_id': 1, 'quantity': 1, 'technician': 'Technician A', 'technician_id': 3, 'state': 'Approved', 'early': 0, 'reason': 'Worn', 'notes': ''});
        await tester.pumpWidget(MaterialApp(theme: machineCareTheme(), home: Workspace(api: api)));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        final pages = ['Equipment', 'Inventory', 'Approvals', 'History', 'Notifications', 'Reports', if (role != 'Technician') ...['Management', 'Reorders', 'Audit log', 'Stock movements']];
        for (final page in pages) {
          if (width < 900) { await tester.tap(find.byTooltip('Open navigation menu')); await tester.pumpAndSettle(); }
          final target = find.widgetWithText(ListTile, page).first;
          await tester.ensureVisible(target); await tester.tap(target); await tester.pumpAndSettle();
          expect(tester.takeException(), isNull, reason: '$role / $page / $width');
        }
      });
    }
  }
  testWidgets('Machine form uses labeled selectors and preserves input after failure', (tester) async {
    final controller = TextEditingController(text: '2');
    await tester.pumpWidget(MaterialApp(theme: machineCareTheme(), home: Scaffold(body: EntryDialog(title: 'Machine', fields: [EntryField('line_id', 'Production line', controller, number: true, options: {'2': 'B01 · Assembly'})], onSave: (_) async { throw Exception('Stale equipment. Reopen to refresh.'); }))));
    expect(find.text('B01 · Assembly'), findsOneWidget);
    await tester.tap(find.text('Save')); await tester.pumpAndSettle();
    expect(find.text('Stale equipment. Reopen to refresh.'), findsOneWidget);
    expect(controller.text, '2');
  });
  testWidgets('Populated operational screens and equipment tree fit a phone', (tester) async {
    tester.view.physicalSize = const Size(390, 844); tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(MaterialApp(theme: machineCareTheme(), home: Workspace(api: PreviewApi('Administrator'))));
    await tester.pumpAndSettle();
    for (final page in ['Equipment','Inventory','Management','Approvals','Reorders','Reports','Audit log','Stock movements']) {
      await tester.tap(find.byTooltip('Open navigation menu')); await tester.pumpAndSettle();
      final target = find.widgetWithText(ListTile, page).first;
      await tester.ensureVisible(target); await tester.tap(target); await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: page);
      if (page == 'Equipment') {
        await tester.enterText(find.widgetWithText(TextField, 'Search machine, asset tag or serial number'), 'DEMO');
        await tester.pumpAndSettle(); expect(tester.takeException(), isNull);
      }
    }
  });
}
