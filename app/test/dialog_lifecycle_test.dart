import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/workspace.dart';

class DialogHarness extends StatefulWidget {
  const DialogHarness({super.key});
  @override
  State<DialogHarness> createState() => _DialogHarnessState();
}
class _DialogHarnessState extends State<DialogHarness> {
  int closes = 0;
  @override
  Widget build(BuildContext context) => Scaffold(body: Column(children: [
    Text('Closed: $closes'),
    TextButton(onPressed: () async {
      final fields = [EntryField('reason', 'Reason', TextEditingController(text: 'Worn seal'))];
      await showDialog<bool>(context: context, builder: (_) => EntryDialog(
        title: 'Request replacement', fields: fields, onSave: (_) async {},
      ));
      if (mounted) setState(() => closes++);
    }, child: const Text('Open request')),
  ]));
}

void main() {
  for (final action in ['Save', 'Cancel']) {
    testWidgets('$action keeps controllers alive through exit transition and allows reopening', (tester) async {
      await tester.pumpWidget(const MaterialApp(home: DialogHarness()));
      for (var attempt = 0; attempt < 2; attempt++) {
        await tester.tap(find.text('Open request'));
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextField), 'Replacement reason');
        await tester.tap(find.text(action));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));
        expect(tester.takeException(), isNull);
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text('Closed: ${attempt + 1}'), findsOneWidget);
      }
    });
  }
}
