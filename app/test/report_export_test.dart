import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/api.dart';
import 'package:machinecare/workspace.dart';

class ExportApi extends Api {
  final calls = <Map<String, dynamic>>[];
  bool fail = false;
  @override Future<Map<String, dynamic>> action(String name, Map<String, dynamic> data) async {
    calls.add({'action': name, ...data});
    if (fail) throw Exception('Export unavailable');
    if (name == 'report_export') return {'filename': 'report.csv', 'csv': '\ufeffquantity\r\n4\r\n', 'row_count': 1};
    return {'records': [], 'has_more': false, 'next_cursor': null};
  }
}
Future<void> launch(WidgetTester tester, Widget widget) async {
  tester.view.physicalSize = const Size(1200, 1000); tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: SingleChildScrollView(child: widget))));
  await tester.pumpAndSettle();
}
void main() {
  testWidgets('Report export requests filtered data and hands filename/content to downloader', (tester) async {
    final api = ExportApi(); String? filename, content;
    await launch(tester, ReportExporter(api: api, role: 'Lead', onDownload: (name, csv) { filename = name; content = csv; }));
    await tester.enterText(find.widgetWithText(TextField, 'Search report records'), 'Seal');
    await tester.tap(find.text('Download CSV')); await tester.pumpAndSettle();
    expect(api.calls.last['report'], 'maintenance'); expect(api.calls.last['search'], 'Seal');
    expect(filename, 'report.csv'); expect(content, '\ufeffquantity\r\n4\r\n');
    expect(find.textContaining('Download requested: 1 rows'), findsOneWidget);
  });
  testWidgets('Technician report selector excludes reorder report', (tester) async {
    await launch(tester, ReportExporter(api: ExportApi(), role: 'Technician', onDownload: (_, __) {}));
    await tester.tap(find.byType(DropdownButtonFormField<String>)); await tester.pumpAndSettle();
    expect(find.text('Reorder history'), findsNothing);
    expect(find.text('Current inventory'), findsOneWidget);
    await tester.tap(find.text('Current inventory')); await tester.pumpAndSettle();
    expect(find.text('Inventory is a current snapshot; date filters do not apply.'), findsOneWidget);
    expect(find.text('From date (UTC)'), findsNothing);
  });
  testWidgets('Export failure preserves input and does not call downloader', (tester) async {
    final api = ExportApi()..fail = true; var downloads = 0;
    await launch(tester, ReportExporter(api: api, role: 'Lead', onDownload: (_, __) { downloads++; }));
    await tester.enterText(find.widgetWithText(TextField, 'Search report records'), 'Seal');
    await tester.tap(find.text('Download CSV')); await tester.pumpAndSettle();
    expect(downloads, 0); expect(find.text('Export unavailable'), findsOneWidget);
    expect(tester.widget<TextField>(find.widgetWithText(TextField, 'Search report records')).controller!.text, 'Seal');
    api.fail = false;
    await tester.tap(find.text('Download CSV')); await tester.pumpAndSettle();
    expect(downloads, 1); expect(find.text('Export unavailable'), findsNothing);
  });
  testWidgets('Record CSV uses current filter fields and ignores loaded-page cursor', (tester) async {
    final api = ExportApi(); var downloads = 0;
    await launch(tester, RecordBrowser(api: api, audit: false, parts: const [], onDownload: (_, __) { downloads++; }));
    await tester.enterText(find.widgetWithText(TextField, 'Search part, SKU, reason or actor'), 'SLIP-1');
    await tester.tap(find.text('Export matching CSV')); await tester.pumpAndSettle();
    expect(api.calls.last['action'], 'report_export'); expect(api.calls.last['report'], 'stock_movements');
    expect(api.calls.last['search'], 'SLIP-1'); expect(api.calls.last.containsKey('cursor'), isFalse);
    expect(downloads, 1); expect(tester.takeException(), isNull);
  });
}
