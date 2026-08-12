// Fill out your copyright notice in the Description page of Project Settings.

#pragma once
#include "CoreMinimal.h"

//把注册方法封装成宏 方便调用
#define ADD_GAME_API(apiname,funcname,handlers) \
FUAutoMsgHandleDelegate apiname; \
apiname.BindStatic(&GameAPI::funcname); \
handlers.Add(#apiname, apiname); 

/**
 * 可以添加一些游戏的API接口 通过自动化进行调用
 */
class GAMEAUTOPLUGIN_API GameAPI
{
public:
    /**
    * @brief 获取当前玩家的位置坐标
    * @param Args
    * @return
    */
    static FString GetLocation(TArray<FString> Args);

    static FString SetLocation(TArray<FString> Args);

    static FString GetPawnRotation(TArray<FString> Args);

    static FString SetControlRotation(TArray<FString> Args);

    static FString GetControlRotation(TArray<FString> Args);

    static FString FindMonsterLocation(TArray<FString> Args);

    static FString FindLongCaoMonster(TArray<FString> Args);

    static FString SetAimRotation(TArray<FString> Args);

    static FString FindMonsterAndAim(TArray<FString> Args);

    static FString UnlockMiniGames(TArray<FString> Args);

    static FString GetBlueprintActorLoc(TArray<FString> Args);

    static FString SetBlueprintActorLoc(TArray<FString> Args);

    static FString SetBlueprintActorMeshLoc(TArray<FString> Args);

    static FString GetMechanismLoc(TArray<FString> Args);

    static FString GetMechanismMaps(TArray<FString> Args);

    static FString GetProjectileLoc(TArray<FString> Args);

    static FString GetIndicatorLoc(TArray<FString> Args);

    static FString GetInteractiveLoc(TArray<FString> Args);

    static FString GetTaskIndicatorLoc(TArray<FString> Args);

    static FString MoveToHandler(TArray<FString> Args);

    static FString IsMoveHandler(TArray<FString> Args);

    static FString SetMoveSpeedHandler(TArray<FString> Args);

    static FString CameraFollowHandler(TArray<FString> Args);

    static FString AimMonsterHandler(TArray<FString> Args);

    static FString CaptureStatHandler(TArray<FString> Args);

    static FString ScenePerfCheckHandler(TArray<FString> Args);

    static FString GetScenePerfData(TArray<FString> Args);

    static FString SetUseAccelerationForPaths(TArray<FString> Args);

    static FString InputAction(TArray<FString> Args);

    static FString ShowScreenText(TArray<FString> Args);

    static FString GTestHandler(TArray<FString> Args);

    static FString SetPawnRotation(TArray<FString> Args);

    static FString GetCondemnLoc(TArray<FString> Args);


    /*TArray<FString> Args 介绍 :
    Args[0]:为方法名 在ADD_GAME_API里面设置的映射名称
    Args[1]:第一个参数
    Args[2]:第二个参数...
    传入的参数类型都是string, 在函数内转换需要的类型

    实现完成的方法 请在UAutoRunner.cpp 使用ADD_GAME_API宏里面进行注册,格式参考已实现的
    */

    /* Add other methods */

    /*
    1.托管行为树
    2.旋转镜头/旋转视角
    3.移动到指定位置
    4.角色跟随镜头
    5.释放技能指定
    */
};
