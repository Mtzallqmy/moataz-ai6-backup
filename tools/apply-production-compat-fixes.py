from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Android 13+ notification permission: make the permission guard explicit so a denied
# notification grant can never surface as SecurityException during boot recovery.
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/agentrun/AgentRunBootRecovery.kt",
    "import android.app.NotificationChannel\nimport android.app.NotificationManager\nimport android.content.Context\nimport android.util.Log\nimport androidx.core.app.NotificationCompat\nimport androidx.core.app.NotificationManagerCompat\n",
    "import android.Manifest\nimport android.app.NotificationChannel\nimport android.app.NotificationManager\nimport android.content.Context\nimport android.content.pm.PackageManager\nimport android.os.Build\nimport android.util.Log\nimport androidx.core.app.NotificationCompat\nimport androidx.core.app.NotificationManagerCompat\nimport androidx.core.content.ContextCompat\n",
)
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/agentrun/AgentRunBootRecovery.kt",
    """            runCatching {
                val nm = context.getSystemService(NotificationManager::class.java) ?: return
""",
    """            runCatching {
                if (
                    Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                    ContextCompat.checkSelfPermission(
                        context,
                        Manifest.permission.POST_NOTIFICATIONS,
                    ) != PackageManager.PERMISSION_GRANTED
                ) {
                    logSafe { Log.i(TAG, \"postAggregateNotification skipped: notification permission denied\") }
                    return
                }
                val nm = context.getSystemService(NotificationManager::class.java) ?: return
""",
)

# 2) LocationTool already gates the whole operation behind PermissionHelper.hasRuntime().
# Android Lint cannot follow that project-local helper across the tool lambda, so document
# the invariant at the function boundary rather than weakening MissingPermission globally.
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/ai/tools/local/LocationTool.kt",
    "import android.Manifest\n",
    "import android.Manifest\nimport android.annotation.SuppressLint\n",
)
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/ai/tools/local/LocationTool.kt",
    "fun locationTool(context: Context): Tool = Tool(\n",
    "@SuppressLint(\"MissingPermission\") // execute() checks ACCESS_FINE_LOCATION before every location API call.\nfun locationTool(context: Context): Tool = Tool(\n",
)

# 3) StrongBox APIs only exist from API 28. Keep Android 8/8.1 support by using the normal
# Android Keystore there, and only request StrongBox behind an SDK guard. Catch Throwable in
# the guarded branch so older runtimes never need to resolve StrongBoxUnavailableException.
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/ai/tools/local/KeystoreTools.kt",
    "import android.security.keystore.KeyGenParameterSpec\n",
    "import android.os.Build\nimport android.security.keystore.KeyGenParameterSpec\n",
)
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/ai/tools/local/KeystoreTools.kt",
    "import android.security.keystore.StrongBoxUnavailableException\n",
    "",
)
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/ai/tools/local/KeystoreTools.kt",
    """                    try {
                        gen.initialize(spec.setIsStrongBoxBacked(true).build())
                        gen.generateKeyPair()
                    } catch (_: StrongBoxUnavailableException) {
                        gen.initialize(spec.setIsStrongBoxBacked(false).build())
                        gen.generateKeyPair()
                    }
""",
    """                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        try {
                            gen.initialize(spec.setIsStrongBoxBacked(true).build())
                            gen.generateKeyPair()
                        } catch (_: Throwable) {
                            gen.initialize(spec.setIsStrongBoxBacked(false).build())
                            gen.generateKeyPair()
                        }
                    } else {
                        gen.initialize(spec.build())
                        gen.generateKeyPair()
                    }
""",
)
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/ai/tools/local/KeystoreTools.kt",
    """                    try {
                        gen.init(spec.setIsStrongBoxBacked(true).build())
                        gen.generateKey()
                    } catch (_: StrongBoxUnavailableException) {
                        gen.init(spec.setIsStrongBoxBacked(false).build())
                        gen.generateKey()
                    }
""",
    """                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        try {
                            gen.init(spec.setIsStrongBoxBacked(true).build())
                            gen.generateKey()
                        } catch (_: Throwable) {
                            gen.init(spec.setIsStrongBoxBacked(false).build())
                            gen.generateKey()
                        }
                    } else {
                        gen.init(spec.build())
                        gen.generateKey()
                    }
""",
)

# 4) MediaMetadataRetriever did not implement AutoCloseable until API 29. Calling Kotlin
# use{} on Android 8/9 can therefore require an API that is absent. release() is supported
# on the whole minSdk range.
replace_once(
    "app/src/main/java/me/rerere/rikkahub/service/MediaPlaybackService.kt",
    """            try {
                MediaMetadataRetriever().use { retriever ->
                    retriever.setDataSource(source)
                    if (resolvedTitle == null)
                        resolvedTitle = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_TITLE)
                    if (resolvedArtist == null)
                        resolvedArtist = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_ARTIST)
                    if (resolvedAlbum == null)
                        resolvedAlbum = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_ALBUM)
                }
            } catch (t: Throwable) { Log.d(TAG, \"metadata extraction failed (best-effort)\", t) }
""",
    """            try {
                val retriever = MediaMetadataRetriever()
                try {
                    retriever.setDataSource(source)
                    if (resolvedTitle == null)
                        resolvedTitle = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_TITLE)
                    if (resolvedArtist == null)
                        resolvedArtist = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_ARTIST)
                    if (resolvedAlbum == null)
                        resolvedAlbum = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_ALBUM)
                } finally {
                    runCatching { retriever.release() }
                }
            } catch (t: Throwable) { Log.d(TAG, \"metadata extraction failed (best-effort)\", t) }
""",
)

# 5) PermissionInfo.getProtection() is API 28. protectionLevel has existed throughout the
# supported range; mask off flags so the comparison uses only the base protection class.
replace_once(
    "app/src/main/java/me/rerere/rikkahub/data/permissions/PermissionInventory.kt",
    "        val protectionBase = info.protection\n",
    "        val protectionBase = info.protectionLevel and PermissionInfo.PROTECTION_MASK_BASE\n",
)

print("Production compatibility fixes applied successfully")
