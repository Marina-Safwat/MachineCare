import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';
import 'reservations_alerts_test.dart' show FakeApi;

/// Seal takes 120 days to arrive and its order was placed long ago.
class LongLeadApi extends FakeApi {
  LongLeadApi() : super(role: 'Lead') { reorderState = 'Ordered'; }
  @override
  Future<Map<String, dynamic>> call(String path, [Map<String, dynamic>? data]) async {
    final state = await super.call(path, data);
    if (path == '/state') {
      state['parts'][0]['lead_days'] = 120;
      state['reorders'][0]['lead_days'] = 120;
      state['reorders'][0]['ordered'] = '2026-01-05T10:00:00+00:00';
    }
    return state;
  }
}

Future<void> open(WidgetTester tester, String page) async {
  tester.view.physicalSize = const Size(1280, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(MaterialApp(home: Workspace(api: LongLeadApi())));
  await tester.pumpAndSettle();
  await tester.tap(find.text(page)); await tester.pumpAndSettle();
}

void main() {
  test('Lead time is written in days, weeks or months', () {
    expect(leadTimeText(0), 'Not set');
    expect(leadTimeText(null), 'Not set');
    expect(leadTimeText(5), '5 days');
    expect(leadTimeText(21), '~3 weeks (21 days)');
    expect(leadTimeText(120), '~4 months (120 days)');
    expect(arrivalEstimate('2026-01-01T00:00:00+00:00', 30), DateTime.parse('2026-01-31T00:00:00+00:00'));
    expect(arrivalEstimate('2026-01-01T00:00:00+00:00', 0), isNull);
  });
  testWidgets('Inventory flags long lead time and when a new order would arrive', (tester) async {
    await open(tester, 'Inventory');
    expect(find.text('Long lead time'), findsOneWidget);
    expect(find.text('~4 months (120 days)'), findsOneWidget);
    expect(find.textContaining('an order placed today arrives around'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Ordered reorder shows expected arrival and an overdue warning', (tester) async {
    await open(tester, 'Reorders');
    expect(find.text('2026-05-05'), findsOneWidget);
    expect(find.textContaining('Delivery overdue by'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
