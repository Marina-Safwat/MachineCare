import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:machinecare/main.dart';

void main() {
  testWidgets('MachineCare displays its login screen', (tester) async {
    await tester.pumpWidget(const MachineCareApp());

    expect(find.text('MachineCare'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'Username'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'Password'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);
  });
}
