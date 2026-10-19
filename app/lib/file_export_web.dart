// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:async';
import 'dart:html' as html;

void downloadCsv(String filename, String content) {
  final blob = html.Blob([content], 'text/csv;charset=utf-8');
  final url = html.Url.createObjectUrlFromBlob(blob);
  final anchor = html.AnchorElement(href: url)..download = filename;
  html.document.body!.append(anchor);
  anchor.click();
  anchor.remove();
  // Let Chrome finish consuming the Blob before releasing it.
  Timer(const Duration(seconds: 60), () => html.Url.revokeObjectUrl(url));
}
