function doPost(e) {
  var contents = JSON.parse(e.postData.contents);
  var event = contents.events[0];
  
  // ログにイベント全体を表示（これで絶対に見逃さない）
  console.log("受信データ: " + JSON.stringify(event));
  
  if (event.source.type === 'group') {
    console.log("【発見】グループID: " + event.source.groupId);
  } else if (event.source.type === 'room') {
    console.log("【発見】トークルームID: " + event.source.roomId);
  }
}
