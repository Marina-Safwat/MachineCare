import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';
import 'reservations_alerts_test.dart' show FakeApi;

class ImportedPartApi extends FakeApi {
  @override
  Future<Map<String, dynamic>> call(String path, [Map<String, dynamic>? data]) async {
    final state = await super.call(path, data);
    state['parts'][0]['provenance'] = {
      'manufacturer': null,
      'manufacturer_part_number': null,
      'reference_serial': '2511231',
      'quantity_per_machine': 5,
      'machine_family': 'Old Auto DIMM / DIMM Press',
      'demo_notice': 'DEMO: stock and planning values require verification.',
    };
    return state;
  }
}

void main() {
  testWidgets('Imported inventory labels sample values and preserves serial meaning on phone', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(MaterialApp(home: Workspace(api: ImportedPartApi())));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Open navigation menu'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, 'Inventory'));
    await tester.pumpAndSettle();
    expect(find.text('Manufacturer: Unknown'), findsOneWidget);
    expect(find.text('Part number: Not supplied'), findsOneWidget);
    expect(find.textContaining('2511231 (not a part number)'), findsOneWidget);
    expect(find.textContaining('Used per machine: 5'), findsOneWidget);
    expect(find.text('Demo stock / planning values'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.enterText(find.byType(TextField).first, '2511231');
    await tester.pumpAndSettle();
    expect(find.textContaining('Used per machine: 5'), findsOneWidget);
  });
}
