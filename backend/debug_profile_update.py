#!/usr/bin/env python3
"""
调试个人资料更新问题
"""

import requests
import json
import sys

def test_profile_update():
    """测试个人资料更新API"""
    
    # 测试默认用户的个人资料更新
    base_url = "http://localhost:8000/api/v1"
    user_id = "3ed4291004c12c2a"
    
    # 首先获取当前个人资料
    print("=== 获取当前个人资料 ===")
    try:
        # 由于需要认证，先尝试直接测试用户信息获取
        response = requests.get(f"{base_url}/user/profile/vocab-status-simple")
        if response.status_code == 200:
            print("✅ API服务正常运行")
            vocab_status = response.json()
            print(f"词汇状态: {vocab_status}")
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"响应: {response.text}")
            return
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return
    
    print("\n=== 测试认证流程 ===")
    
    # 测试微信登录端点（无需真实code）
    login_data = {
        "js_code": "test_debug_code",
        "nickname": "测试用户",
        "avatar_url": "https://example.com/avatar.png"
    }
    
    try:
        login_response = requests.post(f"{base_url}/auth/wechat-login", 
                                       json=login_data, 
                                       timeout=10)
        print(f"登录测试状态码: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get("access_token")
            print(f"✅ 获取到令牌: {token[:20]}..." if token else "❌ 未获取到令牌")
            
            if token:
                # 使用令牌测试个人资料获取
                headers = {"Authorization": f"Bearer {token}"}
                profile_response = requests.get(f"{base_url}/user/profile", headers=headers)
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    print(f"✅ 当前个人资料: {json.dumps(profile_data, indent=2, ensure_ascii=False)}")
                    
                    # 测试个人资料更新
                    update_data = {
                        "nickname": "更新测试用户",
                        "age": 25,
                        "gender": "Male", 
                        "grade": "CET4"
                    }
                    
                    print(f"\n=== 测试个人资料更新 ===")
                    print(f"更新数据: {json.dumps(update_data, indent=2, ensure_ascii=False)}")
                    
                    update_response = requests.put(f"{base_url}/user/profile", 
                                                   json=update_data, 
                                                   headers=headers)
                    
                    print(f"更新状态码: {update_response.status_code}")
                    print(f"更新响应: {update_response.text}")
                    
                    if update_response.status_code == 200:
                        print("✅ 个人资料更新成功")
                        updated_profile = update_response.json()
                        print(f"更新后资料: {json.dumps(updated_profile, indent=2, ensure_ascii=False)}")
                    else:
                        print(f"❌ 个人资料更新失败: {update_response.status_code}")
                        try:
                            error_detail = update_response.json()
                            print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
                        except:
                            print(f"错误响应文本: {update_response.text}")
                else:
                    print(f"❌ 个人资料获取失败: {profile_response.status_code}")
            else:
                print("❌ 无法获取认证令牌，跳过个人资料测试")
        else:
            print(f"❌ 登录失败: {login_response.status_code}")
            print(f"登录响应: {login_response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时，可能是微信API调用问题")
    except Exception as e:
        print(f"❌ 登录测试失败: {e}")

def test_model_validation():
    """测试数据模型验证"""
    print("\n=== 测试数据模型验证 ===")
    
    from app.api.v1.user import UserProfileUpdateRequest
    from pydantic import ValidationError
    
    # 测试有效数据
    try:
        valid_data = UserProfileUpdateRequest(
            nickname="测试用户",
            age=25,
            gender="Male",
            grade="CET4"
        )
        print(f"✅ 有效数据验证通过: {valid_data.dict()}")
    except ValidationError as e:
        print(f"❌ 有效数据验证失败: {e}")
    
    # 测试无效年龄
    try:
        invalid_data = UserProfileUpdateRequest(
            nickname="测试用户", 
            age=-5,  # 无效年龄
            gender="Male",
            grade="CET4"
        )
        print(f"⚠️  无效数据意外通过验证: {invalid_data.dict()}")
    except ValidationError as e:
        print(f"✅ 无效数据正确被拒绝: {e}")

if __name__ == "__main__":
    print("🔍 开始调试个人资料更新问题...\n")
    
    # 测试API连接
    test_profile_update()
    
    # 测试数据模型
    try:
        test_model_validation()
    except ImportError as e:
        print(f"⚠️  模型测试跳过（导入失败）: {e}")
    
    print("\n✅ 调试完成")