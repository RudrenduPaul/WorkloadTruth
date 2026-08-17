Output "/tmp/workloadtruth-demo/docs/demo-verifylog.gif"
Set FontSize 16
Set Width 760
Set Height 260
Set Theme "Dracula"
Set WindowBar Colorful
Set WindowBarSize 36

Type "export PS1='$ '"
Enter
Sleep 300ms

Type "workloadtruth watch --backend synthetic --profile training --interval 0 --window 5 --iterations 2 --log-file workloadtruth.log.jsonl"
Enter
Sleep 2s

Type "workloadtruth verify-log --log-file workloadtruth.log.jsonl"
Enter
Sleep 2s
