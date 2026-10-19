import 'package:flutter/material.dart';

/// Shared visual language: calm surfaces, strong focus, readable controls and
/// status colours that always pair with an icon or word (never colour alone).
class Palette {
  static const brand = Color(0xff0b6b61);
  static const brandSoft = Color(0xffe1f2ef);
  static const ink = Color(0xff142430);
  static const muted = Color(0xff4d5f6b);
  static const border = Color(0xffd8e1e5);
  static const canvas = Color(0xfff2f5f7);
  static const subtle = Color(0xfff7f9fa);
  static const okBg = Color(0xffdcf3e9), okFg = Color(0xff11603f);
  static const warnBg = Color(0xfffff1d2), warnFg = Color(0xff7a4b00);
  static const dangerBg = Color(0xfffde4e1), dangerFg = Color(0xffa3231a);
  static const infoBg = Color(0xffe3eefb), infoFg = Color(0xff1f4f86);
  static const neutralBg = Color(0xffe9eef1), neutralFg = Color(0xff33444f);
}

enum Tone { ok, warn, danger, info, neutral }

({Color bg, Color fg, IconData icon}) toneStyle(Tone tone) => switch (tone) {
  Tone.ok => (bg: Palette.okBg, fg: Palette.okFg, icon: Icons.check_circle_outline),
  Tone.warn => (bg: Palette.warnBg, fg: Palette.warnFg, icon: Icons.schedule),
  Tone.danger => (bg: Palette.dangerBg, fg: Palette.dangerFg, icon: Icons.error_outline),
  Tone.info => (bg: Palette.infoBg, fg: Palette.infoFg, icon: Icons.info_outline),
  Tone.neutral => (bg: Palette.neutralBg, fg: Palette.neutralFg, icon: Icons.circle_outlined),
};

/// Maps workflow and machine states to a consistent tone.
Tone toneFor(String status) {
  if (['Approved', 'Completed', 'Received', 'Operating'].contains(status)) return Tone.ok;
  if (['Pending', 'Early replacement', 'Partially received', 'Maintenance', 'Requested', 'Ordered'].contains(status)) return Tone.warn;
  if (['Rejected', 'Stopped', 'Cancelled'].contains(status)) return Tone.danger;
  if (status.startsWith('Demo')) return Tone.info;
  return Tone.neutral;
}

ThemeData machineCareTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: Palette.brand, primary: Palette.brand, surface: Colors.white, onSurface: Palette.ink, onSurfaceVariant: Palette.muted, outlineVariant: Palette.border);
  const text = TextTheme(
    headlineLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w700, letterSpacing: -.6, color: Palette.ink),
    headlineMedium: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, letterSpacing: -.4, color: Palette.ink),
    headlineSmall: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: Palette.ink),
    titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: Palette.ink),
    titleMedium: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Palette.ink),
    titleSmall: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Palette.ink),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: Palette.ink),
    bodyMedium: TextStyle(fontSize: 15, height: 1.5, color: Palette.ink),
    bodySmall: TextStyle(fontSize: 13, height: 1.45, color: Palette.muted),
    labelLarge: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
    labelMedium: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Palette.muted),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    textTheme: text,
    scaffoldBackgroundColor: Palette.canvas,
    appBarTheme: const AppBarTheme(backgroundColor: Colors.white, surfaceTintColor: Colors.transparent, elevation: 0, scrolledUnderElevation: 1, foregroundColor: Palette.ink, titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: Palette.ink), shape: Border(bottom: BorderSide(color: Palette.border))),
    cardTheme: CardTheme(elevation: 0, color: Colors.white, surfaceTintColor: Colors.transparent, margin: const EdgeInsets.only(bottom: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: const BorderSide(color: Palette.border))),
    inputDecorationTheme: InputDecorationTheme(filled: true, fillColor: Colors.white, contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16), labelStyle: const TextStyle(color: Palette.muted), border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)), enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xff9aaab4))), focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Palette.brand, width: 2))),
    filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(minimumSize: const Size(48, 48), padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)))),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), side: const BorderSide(color: Color(0xff9aaab4)))),
    textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(minimumSize: const Size(48, 48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)))),
    listTileTheme: ListTileThemeData(iconColor: Palette.muted, textColor: Palette.ink, selectedColor: Palette.brand, selectedTileColor: Palette.brandSoft, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
    expansionTileTheme: const ExpansionTileThemeData(shape: Border(), collapsedShape: Border(), iconColor: Palette.brand, collapsedIconColor: Palette.muted),
    dividerTheme: const DividerThemeData(color: Palette.border, space: 24),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
    dialogTheme: DialogTheme(backgroundColor: Colors.white, surfaceTintColor: Colors.transparent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
  );
}

Future<bool> confirmAction(BuildContext context, String title, String message) async =>
    await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: Text(title), content: Text(message), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Go back')), FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Confirm'))])) == true;

/// Coloured status label with an icon, so state is readable without colour.
class StatusPill extends StatelessWidget {
  final String text; final Tone? tone; final IconData? icon;
  const StatusPill(this.text, {super.key, this.tone, this.icon});
  @override Widget build(BuildContext context) {
    final s = toneStyle(tone ?? toneFor(text));
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: s.bg, borderRadius: BorderRadius.circular(999)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(icon ?? s.icon, size: 15, color: s.fg), const SizedBox(width: 6), Flexible(child: Text(text, overflow: TextOverflow.ellipsis, style: TextStyle(color: s.fg, fontWeight: FontWeight.w700, fontSize: 13)))]),
    );
  }
}

/// A labelled value: small muted label above a readable value.
class Fact extends StatelessWidget {
  final String label, value; final double width; final bool strong;
  const Fact(this.label, this.value, {super.key, this.width = 190, this.strong = false});
  @override Widget build(BuildContext context) => SizedBox(width: width, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text(label.toUpperCase(), style: const TextStyle(fontSize: 11.5, letterSpacing: .6, fontWeight: FontWeight.w700, color: Palette.muted)),
    const SizedBox(height: 3),
    Text(value, style: TextStyle(fontSize: strong ? 20 : 15, fontWeight: strong ? FontWeight.w700 : FontWeight.w500, color: Palette.ink)),
  ]));
}

class FactGrid extends StatelessWidget {
  final List<Widget> children;
  const FactGrid(this.children, {super.key});
  @override Widget build(BuildContext context) => Wrap(spacing: 20, runSpacing: 14, children: children);
}

/// Inline banner for warnings and explanations that must not be missed.
class Notice extends StatelessWidget {
  final String text; final Tone tone; final IconData? icon;
  const Notice(this.text, {super.key, this.tone = Tone.info, this.icon});
  @override Widget build(BuildContext context) {
    final s = toneStyle(tone);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(color: s.bg, borderRadius: BorderRadius.circular(10)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Padding(padding: const EdgeInsets.only(top: 2), child: Icon(icon ?? s.icon, size: 18, color: s.fg)), const SizedBox(width: 10), Expanded(child: Text(text, style: TextStyle(color: s.fg, fontWeight: FontWeight.w600, height: 1.4)))]),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String text; final IconData icon;
  const EmptyState(this.text, {super.key, this.icon = Icons.inbox_outlined});
  @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 16), child: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
    Icon(icon, size: 36, color: const Color(0xff9aaab4)), const SizedBox(height: 10),
    Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Palette.muted, fontSize: 15)),
  ])));
}

/// Small heading that separates groups of cards on a page.
class SectionLabel extends StatelessWidget {
  final String text; final int? count;
  const SectionLabel(this.text, {super.key, this.count});
  @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.fromLTRB(4, 8, 4, 10), child: Row(children: [
    Flexible(child: Text(text, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Palette.muted, letterSpacing: .2))),
    if (count != null) ...[const SizedBox(width: 8), CountBadge(count!, tone: Tone.neutral)],
  ]));
}

class CountBadge extends StatelessWidget {
  final int count; final Tone tone;
  const CountBadge(this.count, {super.key, this.tone = Tone.warn});
  @override Widget build(BuildContext context) {
    final s = toneStyle(tone);
    return Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: BoxDecoration(color: s.bg, borderRadius: BorderRadius.circular(999)), child: Text('$count', style: TextStyle(color: s.fg, fontWeight: FontWeight.w700, fontSize: 12.5)));
  }
}

/// Available stock against threshold and target, with the numbers spelled out.
class StockBar extends StatelessWidget {
  final num available, threshold, target;
  const StockBar({super.key, required this.available, required this.threshold, required this.target});
  @override Widget build(BuildContext context) {
    final max = [target, threshold, available, 1].reduce((a, b) => a > b ? a : b).toDouble();
    final tone = available <= 0 ? Tone.danger : available <= threshold ? Tone.warn : Tone.ok;
    return LayoutBuilder(builder: (context, size) => Stack(children: [
      Container(height: 8, decoration: BoxDecoration(color: Palette.neutralBg, borderRadius: BorderRadius.circular(99))),
      Container(height: 8, width: size.maxWidth * (available.clamp(0, max) / max), decoration: BoxDecoration(color: toneStyle(tone).fg, borderRadius: BorderRadius.circular(99))),
      Positioned(left: (size.maxWidth * (threshold.clamp(0, max) / max) - 1).clamp(0, size.maxWidth - 2), child: Container(width: 2, height: 8, color: Palette.ink)),
    ]));
  }
}
