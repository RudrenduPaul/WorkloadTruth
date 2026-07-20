Output docs/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1000
Set Height 560
Set Padding 20
Set Theme "Dracula"

Type "workloadtruth classify --backend synthetic --profile training --samples 10 --interval 0"
Sleep 500ms
Enter
Sleep 3s

Type "workloadtruth benchmark --trials 30 --window 20"
Sleep 500ms
Enter
Sleep 4s
