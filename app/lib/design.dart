import 'package:flutter/material.dart';

/// Shared visual language: calm surfaces, strong focus and readable controls.
ThemeData machineCareTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: const Color(0xff096b62));
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: const Color(0xfff3f6f8),
    appBarTheme: const AppBarTheme(backgroundColor: Colors.white, surfaceTintColor: Colors.transparent, elevation: 0),
    cardTheme: CardTheme(elevation: 0, color: Colors.white, margin: const EdgeInsets.only(bottom: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Color(0xffdde5e8)))),
    inputDecorationTheme: InputDecorationTheme(filled: true, fillColor: const Color(0xfff8fafb), contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18), border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)), enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xff9cabb5))), focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: scheme.primary, width: 2))),
    filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(minimumSize: const Size(48, 48), padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14))),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48))),
    textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(minimumSize: const Size(48, 48))),
    listTileTheme: ListTileThemeData(selectedColor: scheme.primary, selectedTileColor: scheme.primaryContainer.withOpacity(.45), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
    dividerColor: const Color(0xffdde5e8),
    textTheme: const TextTheme(headlineLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w700, letterSpacing: -.8), headlineSmall: TextStyle(fontSize: 24, fontWeight: FontWeight.w700), titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w600), bodyMedium: TextStyle(fontSize: 14, height: 1.5, color: Color(0xff253641))),
  );
}

Future<bool> confirmAction(BuildContext context, String title, String message) async =>
    await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: Text(title), content: Text(message), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Go back')), FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Confirm'))])) == true;
