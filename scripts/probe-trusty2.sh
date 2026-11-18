cd /root/aosp
grep -rn "name: \"libtrustycliinterface\"\|name: \"libtrustystorageinterface\"" --include=Android.bp . 2>/dev/null | head -5
