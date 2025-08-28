#!/usr/bin/env python3
"""
简化版个人资料更新调试
"""

import requests
import json
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.security import create_access_token, generate_user_id

def test_profile_update_with_token():
    """使用手动创建的token测试个人资料更新"""
    
    base_url = "http://localhost:8000/api/v1"
    
    print("=== 创建测试token ===")
    
    # 手动创建一个token用于测试
    test_user_id = "3ed4291004c12c2a"
    test_token = create_access_token(data={"sub": test_user_id})
    
    print(f"✅ 测试token已创建: {test_token[:30]}...")
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    print("\n=== 测试个人资料获取 ===")
    
    try:
        # 获取当前个人资料
        profile_response = requests.get(f"{base_url}/user/profile", headers=headers)
        print(f"个人资料获取状态码: {profile_response.status_code}")
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print(f"✅ 当前个人资料获取成功:")
            print(json.dumps(profile_data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 个人资料获取失败: {profile_response.text}")
            return
            
    except Exception as e:
        print(f"❌ 个人资料获取错误: {e}")
        return
    
    print("\n=== 测试个人资料更新 ===")
    
    # 测试更新数据
    update_data = {
        "nickname": "调试测试用户",
        "age": 28,
        "gender": "Female",
        "grade": "High School"
    }
    
    print(f"更新数据: {json.dumps(update_data, indent=2, ensure_ascii=False)}")
    
    try:
        # 更新个人资料
        update_response = requests.put(f"{base_url}/user/profile", 
                                       json=update_data, 
                                       headers=headers)
        
        print(f"更新状态码: {update_response.status_code}")
        print(f"更新响应: {update_response.text}")
        
        if update_response.status_code == 200:
            print("✅ 个人资料更新成功！")
            updated_profile = update_response.json()
            print(f"更新后的资料: {json.dumps(updated_profile, indent=2, ensure_ascii=False)}")
            
            # 验证更新是否成功
            print("\n=== 验证更新结果 ===")
            verify_response = requests.get(f"{base_url}/user/profile", headers=headers)
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                print("验证结果:")
                for key, expected_value in update_data.items():
                    actual_value = verify_data.get(key)
                    status = "✅" if actual_value == expected_value else "❌"
                    print(f"  {status} {key}: 期望={expected_value}, 实际={actual_value}")
            else:
                print(f"❌ 验证失败: {verify_response.status_code}")
                
        elif update_response.status_code == 422:
            print("❌ 数据验证错误")
            try:
                error_detail = update_response.json()
                print(f"验证错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                pass
        else:
            print(f"❌ 个人资料更新失败")
            try:
                error_detail = update_response.json()
                print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                pass
                
    except Exception as e:
        print(f"❌ 个人资料更新错误: {e}")

def test_available_grades():
    """测试可用年级获取"""
    print("\n=== 测试可用年级获取 ===")
    
    base_url = "http://localhost:8000/api/v1"
    
    try:
        grades_response = requests.get(f"{base_url}/user/profile/grades")
        print(f"可用年级获取状态码: {grades_response.status_code}")
        
        if grades_response.status_code == 200:
            grades_data = grades_response.json()
            print("✅ 可用年级列表:")
            for grade in grades_data:
                print(f"  - {grade.get('grade')} ({grade.get('description', 'No description')})")
        else:
            print(f"❌ 可用年级获取失败: {grades_response.text}")
    except Exception as e:
        print(f"❌ 可用年级获取错误: {e}")

if __name__ == "__main__":
    print("🔧 开始个人资料更新简化调试...\n")
    
    # 测试可用年级
    test_available_grades()
    
    # 测试个人资料更新
    test_profile_update_with_token()
    
    print("\n✅ 调试完成")