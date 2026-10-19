import 'package:flutter/material.dart';
import 'api.dart';
import 'workspace.dart';
import 'design.dart';

void main() => runApp(const MachineCareApp());
class MachineCareApp extends StatelessWidget {
  const MachineCareApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'MachineCare', debugShowCheckedModeBanner: false,
    theme: machineCareTheme(),
    home: const LoginPage(),
  );
}
class LoginPage extends StatefulWidget {
  const LoginPage({super.key});
  @override State<LoginPage> createState() => _LoginPageState();
}
class _LoginPageState extends State<LoginPage> {
  final api = Api();
  final username = TextEditingController(), password = TextEditingController();
  bool busy = false, obscure = true; String? error;
  @override void dispose() { username.dispose(); password.dispose(); super.dispose(); }
  Future<void> login() async {
    if (busy) return;
    if (username.text.trim().isEmpty || password.text.isEmpty) {
      setState(() => error = 'Enter your username and password.');
      return;
    }
    setState(() { busy = true; error = null; });
    try {
      final user = await api.login(username.text.trim(), password.text);
      if (!mounted) return;
      if (user['must_change'] == 1) {
        final changed = await changePassword(context, api);
        api.token = null;
        if (mounted) setState(() { error = changed ? 'Password changed. Sign in with your new password.' : 'You must change your temporary password to continue.'; });
      } else {
        await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => Workspace(api: api)));
        api.token = null; if (mounted) password.clear();
      }
    } catch (e) { if (mounted) setState(() => error = cleanError(e)); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => Scaffold(body: Center(child: SingleChildScrollView(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 460), child: Padding(padding: const EdgeInsets.all(24), child: Card(child: Padding(padding: const EdgeInsets.all(32), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    const Icon(Icons.precision_manufacturing_outlined, size: 52, color: Color(0xff0c756c)), const SizedBox(height: 16),
    Text('MachineCare', textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineLarge),
    const SizedBox(height: 8), const Text('Equipment. Inventory. Accountability.', textAlign: TextAlign.center), const SizedBox(height: 28),
    const Text('LOCAL WORKSPACE', textAlign: TextAlign.center, style: TextStyle(fontSize: 11, letterSpacing: 1.5)), const SizedBox(height: 20),
    TextField(controller: username, autofocus: true, autofillHints: const [AutofillHints.username], textInputAction: TextInputAction.next, decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person_outline)), enabled: !busy), const SizedBox(height: 16),
    TextField(controller: password, obscureText: obscure, autofillHints: const [AutofillHints.password], decoration: InputDecoration(labelText: 'Password', prefixIcon: const Icon(Icons.lock_outline), suffixIcon: IconButton(tooltip: obscure ? 'Show password' : 'Hide password', onPressed: () => setState(() => obscure = !obscure), icon: Icon(obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined))), enabled: !busy, onSubmitted: (_) { if (!busy) login(); }), const SizedBox(height: 20),
    if (error != null) Padding(padding: const EdgeInsets.only(bottom: 16), child: Text(error!, style: const TextStyle(color: Color(0xffb3261e)))),
    FilledButton(onPressed: busy ? null : login, child: Padding(padding: const EdgeInsets.all(14), child: Text(busy ? 'Signing in…' : 'Sign in'))),
    const SizedBox(height: 18), const Text('Accounts are provided by your administrator.\nNo public registration.', textAlign: TextAlign.center),
  ]))))))));
}
