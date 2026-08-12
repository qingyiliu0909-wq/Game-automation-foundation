// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"

#define ADD_UAUTO_API(apiname,funcname,handlers) \
FUAutoMsgHandleDelegate apiname; \
apiname.BindStatic(&UAutoAPI::funcname); \
handlers.Add(#apiname, apiname); 


/**
 * Implementation of automation basic interface
 * Args: Parameters passed from the control end
 */
class  UAutoAPI
{
public:
	/**
	 * @brief Client stops connecting
	 * @param Args
	 * @return
	 */
	static FString CloseConnectionHandler(TArray<FString> Args);
	/**
	 * @brief Get plugin version
	 * @param Args
	 * @return
	 */
	static FString GetPluginVersion(TArray<FString> Args);

	static FString SwitchWaysHandler(TArray<FString> Args);

	static FString SwitchExcludeNotVisibleHandler(TArray<FString> Args);


	/**
	 * @brief Get Engine version
	 * @param Args
	 * @return
	 */
	static FString GetEngineVersion(TArray<FString> Args);

	/**
	*@brief Get Engine version
	* @param Args
	* @return
	*/
	static FString GetAppNameHandler(TArray<FString> Args);

	/**
	 * @brief Enable script recording
	 * @param Args 
	 * @return
	 */
	static FString DebugModeHandler(TArray<FString> Args);

	/**
	 * @brief Get game resolution
	 * @param Args
	 * @return
	 */
	static FString GetScreenHandler(TArray<FString> Args);

	/**
	 * @brief Execute UE command
	 * @param Args
	 * @return
	 */
	static FString ExecuteConsoleCommand(TArray<FString> Args);

	/**
	 * @brief 查找 Widget
	 * @param Args
	 * @return
	 */
	static FString FindObjectHandler(TArray<FString> Args);

	/**
	 * @brief 对指定的 UButton 执行点击事件
	 * @param Args
	 * @return
	 */
	static FString TapObjectHandler(TArray<FString> Args);

	/**
	 * @brief 对指定的 SWidget 执行点击事件
	 * @param Args
	 * @return
	 */
	static FString MouseDownHandler(TArray<FString> Args);
	/**
 * @brief 获取指定 Widget 的文本（必须是文本控件）
 * @param Args
 * @return
 */
	static FString GetTextHandler(TArray<FString> Args);

	/**
	 * @brief 设置指定 Widget 的文本（必须是文本控件）
	 * @param Args
	 * @return
	 */
	static FString SetTextHandler(TArray<FString> Args);

	/**
	 * @brief 查找指定路径下 Widget 的子 Widget
	 * @param Args
	 * @return
	 */
	static FString FindChildHandler(TArray<FString> Args);

	/**
	 * @brief 判断指定 Widget 是否存在
	 * @param Args
	 * @return
	 */
	static FString ObjectExistHandler(TArray<FString> Args);

	/**
	 * @brief 判断指定 Widget 是否存在 存在就点击
	 * @param Args
	 * @return
	 */
	static FString ObjectExistOnlyTapHandler(TArray<FString> Args);

	/**
	 * @brief 搜索包含对应文本的所有文本控件
	 * @param Args
	 * @return
	 */
	static FString FindTextHandler(TArray<FString> Args);

	/**
	 * @brief 获取指定 Widget 的父 Widget
	 * @param Args
	 * @return
	 */
	static FString GetParentHandler(TArray<FString> Args);

	/**
	 * @brief 执行点击视窗坐标
	 * @param Args
	 * @return
	 */
	static FString TapScreenHandler(TArray<FString> Args);

	/**
	 * @brief 点击屏幕
	 * @param Args
	 * @return
	 */
	static FString ClickScreenHandler(TArray<FString> Args);

	/**
	 * @brief 查找文本并点击坐标
	 * @param Args
	 * @return
	 */
	static FString FindTextAndWhichClickHandler(TArray<FString> Args);

	/**
	 * @brief 内存报告采集
	 * @param Args
	 * @return
	 */
	static FString MemReportHandler(TArray<FString> Args);

	/**
	 * @brief 打印 UE Log
	 * @param Args
	 * @return
	 */
	static FString LogHandler(TArray<FString> Args);

	/**
	 * @brief 设置 ListView 的滑动进度
	 * @param Args
	 * @return
	 */
	static FString SetScrollOffsetHandler(TArray<FString> Args);

	/**
	 * @brief 修改路径获取模式
	 * @param Args
	 * @return
	 */
	static FString SwitchModeHandler(TArray<FString> Args);

	/**
	 * @brief 获取地图名
	 * @param Args
	 * @return
	 */
	static FString GetMapName(TArray<FString> Args);

	/**
	 * @brief 获取日志文件列表
	 * @param Args
	 * @return
	 */
	static FString GetLogFileList(TArray<FString> Args);

	/**
	 * @brief 修按名称查找Actor
	 * @param Args
	 * @return
	 */
	static FString FindActorByNameHandler(TArray<FString> Args);

	
	/**
	 * @brief 获取log文件的信息
	 * @param Args
	 * @return
	 */
	static FString GetLogFileInfo(TArray<FString> Args);

	static FString GetLogFileContent(TArray<FString> Args);

	/**
	 * @brief 读取日志文件尾部内容，优先用于页面实时预览
	 * @param Args [cmd, fileName, tailBytes]
	 * @return
	 */
	static FString GetLogFileTail(TArray<FString> Args);

	/**
	 * @brief 按偏移读取日志文件内容，优先用于下载大日志
	 * @param Args [cmd, fileName, offset, readBytes]
	 * @return
	 */
	static FString GetLogFileChunk(TArray<FString> Args);

	static FString InputKeys(TArray<FString> Args);

	static FString InputAxis(TArray<FString> Args);

	/* Add other methods */
	static FString TestHandler(TArray<FString> Args);

};
