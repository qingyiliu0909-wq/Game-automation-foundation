// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class GameAutoPlugin : ModuleRules
{
	public GameAutoPlugin(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
        bEnableExceptions = true;
        PublicIncludePaths.AddRange(
			new string[] {
				// ... add public include paths required here ...
				ModuleDirectory
            }
			);
				
		
		PrivateIncludePaths.AddRange(
			new string[] {
				// ... add other private include paths required here ...
			}
			);
			
		
		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				// ... add other public dependencies that you statically link with here ...
                "UMG",
                "Json",
                "UnLua",
                "Lua",
                "JsonUtilities",
                "Networking",
                "TraceLog",
                "Http",
                "InputCore",
                "CoreUObject",
                "Engine",
                "TraceLog",
                "EM",
                "AIModule",
				"NavigationSystem",
                "RHI",
            }
			);
        if (Target.bBuildEditor)
        {
            PublicDependencyModuleNames.AddRange(
                new string[]
                {
                    "UnrealEd"
                }
            );
        }

        PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"CoreUObject",
				"Engine",
				"Slate",
				"SlateCore",
				// ... add private dependencies that you statically link with here ...	
				"Sockets",
                "Networking",
				//"HotPatch",
            }
			);
		
		
		DynamicallyLoadedModuleNames.AddRange(
			new string[]
			{
				// ... add any modules that your module loads dynamically here ...
			}
			);
	}
}
