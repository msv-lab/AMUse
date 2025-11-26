## TODO
~~1. Fix analyser.dl by replacing the 'call_name(_, t, t_base, t_meth_sig)' with 'label(t, t_meth_sig), variable(t_base, t_meth_sig).'~~

1. `this_unknown.next()` produced via spoon cannot work. Need to break the chain of calls.
2. `jackrabbit/misuses/12/misuse.yml` actually is interprocedural. 
~~3. Define use_of_var: `use_of_var(V, N, IN_METHD)` where `V` is the variable used at node `N`, `IN_METHD` is the method name where the variable is used. The use should include call, return, for loop condition, while loop condition, if condition, etc.~~ No need for this.
4. Fix the `call_name` fact in Factor.
5. Fix the `must_followed_by`.

## NOTE
1. The following are removed from MUBench dataset since they are not java.util.Map
```
        {
            "id": "closure.319.mudetectxp-16",
            "folder_path": "/root/checkouts/closure/319/checkout/",
            "file_path": "/root/checkouts/closure/319/checkout/src/com/google/javascript/jscomp/SimpleDefinitionFinder.java",
            "api_line_no": 159 //remove, since it is not java.util.Map
        },
        {
            "id": "closure.319.mudetectxp-17",
            "folder_path": "/root/checkouts/closure/319/checkout/",
            "file_path": "/root/checkouts/closure/319/checkout/src/com/google/javascript/jscomp/SimpleDefinitionFinder.java",
            "api_line_no": 159 //remove, since it is not java.util.Map
        },
```

2. This is inter procedural
```
        {
            "id": "jackrabbit.3189.12",
            "folder_path": "/root/checkouts/jackrabbit/3189/checkout/",
            "file_path": "/root/checkouts/jackrabbit/3189/1.java",
            "api_line_no": 92 
        }
```

3. This bug is a true negative. Because although there is `hasNext()`, `next()` is called twice within its domain.
```
        {
            "id": "thomas-s-b-visualee.410a80f.29",
            "folder_path": "/root/checkouts/thomas-s-b-visualee/410a80f/checkout",
            "file_path": "/root/checkouts/thomas-s-b-visualee/410a80f/checkout/src/main/java/de/strullerbaumann/visualee/examiner/Examiner.java",
            "api_line_no": 251
        }
```

4. The API of the following actually should be `android.app.ProgressDialog.dismiss()` instead of `android.app.Dialog.dismiss()`

```
        {
            "id": "tucanmobile.27.1",
            "folder_path": "/root/checkouts/TuCanMobile-373d4b9e5da9c60a59055c41a5f81c073941c936/",
            "file_path": "/root/checkouts/TuCanMobile-373d4b9e5da9c60a59055c41a5f81c073941c936/src/com/dalthed/tucan/Connection/SimpleSecureBrowser.java",
            "api_line_no": 60
        }
```

5. `ResultSet.next()` throws exceptions. The following bugs need exception handling rule:

"chensun.cf23b99.jadet-2"
"chensun.cf23b99.jadet-2a"
"chensun.cf23b99.jadet-5"
"chensun.cf23b99.jadet-5a"


6. `/root/AMUse-data/downloaded_code_snippets/java.io@DataOutputStream+java.io@DataOutputStream@close/raw_15.java` cannot be a sample since throw + finally is not supported yet in spoon.

7. spoon will will parse the `dos.close()` in `/root/AMUse-data/downloaded_code_snippets/java.io@DataOutputStream+java.io@DataOutputStream@close/raw_6.java` to `FilterOutputStream`, which seems to be a bug of spoon.


8. `tbuktu-ntru.8126929.473` and `tbuktu-ntru.8126929.474` are inter-procedural. 
`caller point`: `/root/checkouts/tbuktu-ntru/8126929/build/src/test/java/net/sf/ntru/encrypt/EncryptionKeyPairTest.java`.
`tbuktu-ntru.8126929.475` and `tbuktu-ntru.8126929.476` need to add `close()` instead of `flush()`. They can be classified into `"java.io.DataOutputStream.close"` bugs in `mubench.json` to avoid extra work.

9. `jodatime-27` is missing in the datasets.yml.

10. `jodatime.cc35fb2.339` is not a typical missing `flush()` bug. https://github.com/emopers/joda-time/commit/60be421469dd85893978bfc645b41e94c63ba1b1

11. The following two samples cannot be handled, since we need to break the long call first.
```
        {
            "id": 5,
            "method_line_no": 634,
            "api_instance": "implemented",
            "in_method": "expectAllInterfaceProperties()",
            "file_path": "/root/AMUse-data/tabnine/com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype/5.java"
        }

        {
            "id": 8,
            "method_line_no": 889,
            "api_instance": "implemented",
            "in_method": "expectAllInterfaceProperties()",
            "file_path": "/root/AMUse-data/tabnine/com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype/8.java"
        },
```




## Comments
1. `condition_dominate` is correct now. 30/12/2023
2. `must_preceeded_by` is fixed by exposing caller variable to the predicate. 30/12/2023
3. For each component rule, some arguments are used to represent the first api element and the second api element, respectively.

4. 5, 7, 3 are not java.util.Iterator 4/1/2023.
```
        {
            "id": 3,
            "method_line_no": 58,
            "api_instance": "iterator",
            "in_method": "filter",
            "file_path": "/root/AMUse-data/downloaded_code_snippets/java.util@Iterator@hasNext+java.util@Iterator@next/raw_3.java"
        },
        ...
```

5. 8 is not typical sample for android.app.Dialog.dismiss(). 4/1/2023.

```
        {
            "id": 8,
            "method_line_no": 214,
            "api_instance": "",
            "in_method": "dismissDialogSafe",
            "file_path": "/root/AMUse-data/downloaded_code_snippets/android.app@Dialog@dismiss+android.app@Dialog@isShowing/raw_8.java"
        },
```

6. 4 and 8 of `java.sql.Connection.prepareStatement+java.sql.PreparedStatement.close` require call breaks.

7. `java.sql.Connection.prepareStatement+java.sql.PreparedStatement.close`'s 2 and 4 are parsed to `java.io.FilterOutputStream.close()` instead of `java.io.OutputStream.close()` via spoon.

8. cannot find the bug: "https://github.com/stg-tud/MUBench/blob/master/data/closure/misuses/4/misuse.yml" in MuBench

9. `property-management-76260865`, `webtend.8fe8f4f.1` are missing from MuBench. 

10. The two bugs under `org.testng.reporters.XMLStringBuffer` are not API misuses. They are just bugs. 7/1/2023

11. `com.google.javascript.rhino.jstype.UnionTypeBuilder` is not API misuse. 7/1/2023.
`com.google.javascript.rhino.jstype.ObjectType` is not API misuse. 7/1/2023.

12. link of `com.google.gson.JsonElement` is broken. 7/1/2023.

## Explanation on evaluation results
```[csv]
java.sql@Connection@prepareStatement+java.sql@PreparedStatement@close, PASS, 5
android.database@Cursor@close+android.database.sqlite@SQLiteDatabase@query, PASS, 1
java.sql@PreparedStatement@executeQuery+java.sql@ResultSet@close, PASS, 7
java.io.PrintWriter@close, PASS, 1
javax.swing@JFrame@pack+javax.swing@JFrame@setVisible, PASS, 2
java.util.Enumeration@nextElement, FAIL, 1, 1
java.nio@ByteBuffer@flip+java.nio.channels@FileChannel@write, PASS, 1
java.io@DataOutputStream+java.io@DataOutputStream@close, PASS, 3
java.util@Scanner@hasNext+java.util@Scanner@next, PASS, 3
java.util@Iterator@hasNext+java.util@Iterator@next, FAIL, 17, 1
java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream, FAIL, 43, 1
java.lang.Short.parseShort, PASS, 3
java.net.URLDecoder@decode, NO_ANALYSER
com.google.javascript.rhino.jstype.ObjectType.getImplicitPrototype, PASS, 1
java.lang.String@getBytes, NO_ANALYSER
android.app@Dialog@dismiss+android.app@Dialog@isShowing, FAIL, 1, 1
java.util.Map@get, FAIL, 3, 1
```

1. android.app@Dialog@dismiss+android.app@Dialog@isShowing, FAIL, 1, 1
    The API actually is android.app.ProgressDialog.dismiss(). It is annotated incorrectly in MUbench.
2. java.util.Enumeration@nextElement, FAIL, 1, 1
    An error from my end. Can be fixed.
3. `jodatime.cc35fb2.339` is the failed in java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream.
    This misuse is inter-procedural, which we cannot handle at the moment.
4. java.util@Iterator@hasNext+java.util@Iterator@next
  This bug is a true negative. Because although there is `hasNext()`, `next()` is called twice within its domain. We can avoid so by modifying the rule to include the number of calls to the next() method. However, Symlog does not support the 'count' operator. A method to bypass this is to gradually mask the detected calls and run the analysis again.

## MUBECH Comments
1. "java.lang.String":
        {
            "id": "adempiere.1312.1",
            "folder_path": "",
            "file_path": "/root/checkouts/adempiere/1312/Secure.java",
            "api_line_no": 173
        }

Spoon cannot parse the file. "The type Secure is already defined" error. So, remove it from the mubench.json.

2. "com.unity3d.player.UnityPlayerActivity": [
        {
            "id": "openiab.62.1",
            "folder_path": "/root/checkouts/OpenIAB/unity_plugin",
            "file_path": "/root/checkouts/OpenIAB/unity_plugin/src/com/openiab/BillingActivity.java",
            "api_line_no": 25
        }
    ],

No corresponding API in the parsed facts. So, remove it from the mubench.json.

3.     "android.app.ListFragment.getListView": [
        {
            "id": "wordpressa.1928.1",
            "folder_path": "/root/checkouts/WordPress-Android-ab3c44cae294a02bc5b195f396d4eb9ebd462cdd/WordPress",
            "file_path": "/root/checkouts/WordPress-Android-ab3c44cae294a02bc5b195f396d4eb9ebd462cdd/WordPress/src/main/java/org/wordpress/android/ui/notifications/NotificationsListFragment.java",
            "api_line_no": 202
        }
    ],

No corresponding API in the parsed facts. So, remove it from the mubench.json.

4.     "android.content.Intent.getLongExtra": [
        {
            "id": "gnucrasha.221.1a",
            "folder_path": "/root/checkouts/gnucash-android",
            "file_path": "/root/checkouts/gnucash-android/app/src/org/gnucash/android/ui/passcode/PassLockActivity.java",
            "api_line_no": 24
        },
        {
            "id": "gnucrasha.221.1b",
            "folder_path": "/root/checkouts/gnucash-android",
            "file_path": "/root/checkouts/gnucash-android/app/src/org/gnucash/android/ui/passcode/PasscodeLockScreenActivity.java",
            "api_line_no": 47
        }
    ],
Cannot find the corresponding API in the parsed facts. So, remove it from the mubench.json.

5.     "java.util.SortedMap.firstKey": [
        {
            "id": "lucene.1918.2",
            "folder_path": "/root/checkouts/lucene/1918/build",
            "file_path": "/root/checkouts/lucene/1918/build/src/java/org/apache/lucene/index/ParallelReader.java",
            "api_line_no": 474
        }
    ],
Cannot find the corresponding API in the parsed facts. So, remove it from the mubench.json. 

6.     "java.util.Collections$SynchronizedCollection": [
        {
            "id": "testng.cd80791.21",
            "folder_path": "/root/checkouts/testng/cd80791/build",
            "file_path": "/root/checkouts/testng/cd80791/build/src/main/java/org/testng/reporters/jq/Model.java",
            "api_line_no": 43
        },
        {
            "id": "testng.92e7da1.18",
            "folder_path": "/root/checkouts/testng/92e7da1/build",
            "file_path": "/root/checkouts/testng/92e7da1/build/src/main/java/org/testng/reporters/JUnitXMLReporter.java",
            "api_line_no": 148
        },
        {
            "id": "testng.677302c.22",
            "folder_path": "/root/checkouts/testng/677302c/build",
            "file_path": "/root/checkouts/testng/677302c/build/src/main/java/org/testng/reporters/XMLReporter.java",
            "api_line_no": 149
        },
        {
            "id": "testng.92e7da1.17",
            "folder_path": "/root/checkouts/testng/92e7da1/build",
            "file_path": "/root/checkouts/testng/92e7da1/build/src/main/java/org/testng/reporters/JUnitXMLReporter.java",
            "api_line_no": 148
        },
        {
            "id": "testng.d6dfce3.16",
            "folder_path": "/root/checkouts/testng/d6dfce3/build",
            "file_path": "/root/checkouts/testng/d6dfce3/build/src/main/java/org/testng/reporters/jq/ChronologicalPanel.java",
            "api_line_no": 30
        }
    ]
Cannot parse the files. So, remove them from the mubench.json.

7. The following projects are removed from mubench.json since they cannot be parsed by spoon, or the corresponding API cannot be found in the parsed facts.

Project Calligraphy.2 not found in mubench.json

Project Adempiere.1 not found in mubench.json

Project Gnucrasha.1a not found in mubench.json

Project Gnucrasha.1b not found in mubench.json

Project Jodatime.1 not found in mubench.json

Project Lucene.2 not found in mubench.json

Project Openiab.1 not found in mubench.json

Project testng.16 not found in mubench.json

Project testng.17 not found in mubench.json

Project testng.18 not found in mubench.json

Project testng.21 not found in mubench.json

Project testng.22 not found in mubench.json

Project Wordpressa.1 not found in mubench.json

8. The following API usages are missing because spoon cannot parse non-public classes.
Missing usages for lucene.1251 java.io.File.createNewFile org.apache.lucene.store.SimpleFSLock.obtain(): 1
Missing usages for asterisk-java.304421c java.util.Map.put org.asteriskjava.live.internal.AsteriskChannelImpl.setVariable(java.lang.String,java.lang.String): 1
Missing usages for asterisk-java.41461b4 java.util.Map.put org.asteriskjava.live.internal.AsteriskChannelImpl.updateVariable(java.lang.String,java.lang.String): 1
Missing usages for asterisk-java.41461b4 java.util.Map.put org.asteriskjava.manager.internal.ManagerConnectionImpl.sendAction(org.asteriskjava.manager.action.ManagerAction,org.asteriskjava.manager.SendActionCallback): 1
Missing usages for jackrabbit.2681 java.lang.Boolean.getBoolean org.apache.jackrabbit.core.persistence.xml.XMLPersistenceManager.readState(org.apache.jackrabbit.core.util.DOMWalker,org.apache.jackrabbit.core.state.PropertyState): 1
Missing usages for jackrabbit.2681 java.lang.Short.parseShort org.apache.jackrabbit.core.persistence.xml.XMLPersistenceManager.readState(org.apache.jackrabbit.core.util.DOMWalker,org.apache.jackrabbit.core.state.NodeState): 1
Missing usages for jackrabbit.2681 java.lang.Short.parseShort org.apache.jackrabbit.core.persistence.xml.XMLPersistenceManager.readState(org.apache.jackrabbit.core.util.DOMWalker,org.apache.jackrabbit.core.state.PropertyState): 1
Missing usages for jmrtd.67 javax.crypto.Cipher.doFinal sos.mrtd.PassportAuthService.doAA(java.security.PublicKey): 1
Missing usages for httpclient.302 org.apache.commons.httpclient.HttpConnection.open org.apache.commons.httpclient.HttpMethodDirector.executeWithRetry(org.apache.commons.httpclient.HttpMethod): 1
Missing usages for httpclient.444 org.apache.commons.httpclient.HttpConnection.open org.apache.commons.httpclient.HttpMethodDirector.executeWithRetry(org.apache.commons.httpclient.HttpMethod): 1
Missing usages for httpclient.444 org.apache.commons.httpclient.auth.AuthState.isPreemptive org.apache.commons.httpclient.HttpMethodDirector.processProxyAuthChallenge(org.apache.commons.httpclient.HttpMethod): 1
Missing usages for httpclient.444 org.apache.commons.httpclient.auth.AuthState.isPreemptive org.apache.commons.httpclient.HttpMethodDirector.processWWWAuthChallenge(org.apache.commons.httpclient.HttpMethod): 1
Total missing usages: 12

9. The following API usages's source code cannot be found in GitHub.

        {
            "id": "corona-old.0d0d18b.3",
            "folder_path": "/root/checkouts/corona-old/0d0d18b/build",
            "file_path": "/root/checkouts/corona-old/0d0d18b/build/src/com/corona/crypto/DESCypher.java",
            "api_line_no": 62
        },
        {
            "id": "corona-old.0d0d18b.4",
            "folder_path": "/root/checkouts/corona-old/0d0d18b/build",
            "file_path": "/root/checkouts/corona-old/0d0d18b/build/src/com/corona/crypto/DESCypher.java",
            "api_line_no": 83
        },
        {
            "id": "saavn.e576758.1",
            "folder_path": "/root/checkouts/saavn/e576758/build",
            "file_path": "/root/checkouts/saavn/e576758/build/src/saavn/cz/vity/freerapid/plugins/services/saavn/SaavnFileRunner.java",
            "api_line_no": 108
        },
        {
            "id": "secure-tcp.aeba19a.1",
            "folder_path": "/root/checkouts/secure-tcp/aeba19a/build",
            "file_path": "/root/checkouts/secure-tcp/aeba19a/build/src/main/java/org/network/stcp/server/SecureConnectionHandler.java",
            "api_line_no": 36
        },
        {
            "id": "technic-launcher-sp.7809682.1",
            "folder_path": "/root/checkouts/technic-launcher-sp/7809682/build",
            "file_path": "/root/checkouts/technic-launcher-sp/7809682/build/src/main/java/org/spoutcraft/launcher/encryption/EncryptionUtil.java",
            "api_line_no": 253
        },
        {
            "id": "minecraft-launcher.e62d1bb.1",
            "folder_path": "/root/checkouts/minecraft-launcher/e62d1bb/build",
            "file_path": "/root/checkouts/minecraft-launcher/e62d1bb/build/src/main/java/net/minecraft/launcher/authentication/BaseAuthenticationService.java",
            "api_line_no": 30
        },
        {
            "id": "warwalk.9c85f74.1",
            "folder_path": "/root/checkouts/warwalk/9c85f74/build",
            "file_path": "/root/checkouts/warwalk/9c85f74/build/src/main/java/net/warwalk/ww/WW.java",
            "api_line_no": 59
        },
        {
            "id": "yapps.1ae52b0.1",
            "folder_path": "",
            "file_path": "",
            "api_line_no": -1
        },

        {
            "id": "itext.5091.1",
            "folder_path": "/root/checkouts/itext/5091/build/itext",
            "file_path": "/root/checkouts/itext/5091/build/itext/src/main/java/com/itextpdf/text/pdf/PdfPublicKeySecurityHandler.java",
            "api_line_no": 253
        },
10. The following is not a third-party API misuse.

"com.vaguehope.onosendai.util.BatteryHelper.level": [
        {
            "id": "onosendai.100.1",
            "folder_path": "/root/checkouts/onosendai/100",
            "file_path": "/root/checkouts/onosendai/100/src/main/java/com/vaguehope/onosendai/update/AlarmReceiver.java",
            "api_line_no": 29
        }
    ],
11. lnreadera.1 is removed since we do not handle 'onDestroy' method yet.

## TODO:
- []: Datalog rules of all sampled APIs.
