import os
import sys
import subprocess
import webbrowser

def main():
    print("=" * 60)
    print("        [GitHub 계정 연동 및 첫 리포트 업로드]")
    print("=" * 60)
    print("\n💡 진행 안내:")
    print("1. 잠시 후 터미널에 '8자리 코드(예: ABCD-1234)'가 표시됩니다.")
    print("2. Enter 키를 누르면 GitHub 로그인 웹페이지가 자동으로 열립니다.")
    print("3. 브라우저에 해당 코드를 입력하고 [Authorize] 버튼을 눌러주세요.\n")
    print("=" * 60 + "\n")

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    gh_bin = os.path.join(local_app_data, r"Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe")
    git_bin = os.path.join(local_app_data, r"Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe")

    if not os.path.exists(gh_bin):
        print(f"❌ GitHub CLI 실행 파일을 찾을 수 없습니다: {gh_bin}")
        return

    if not os.path.exists(git_bin):
        print(f"❌ Git 실행 파일을 찾을 수 없습니다: {git_bin}")
        return

    # 1. GitHub CLI 웹 로그인 실행
    try:
        print("🔗 GitHub 웹 인증을 시작합니다...")
        res = subprocess.run([gh_bin, "auth", "login", "--web", "--git-protocol", "https", "-h", "github.com"])
        if res.returncode != 0:
            print("\n❌ GitHub 로그인이 취소되었거나 실패했습니다.")
            return
    except Exception as e:
        print(f"\n❌ 인증 실행 중 오류 발생: {e}")
        return

    print("\n✅ GitHub 계정 인증 성공!")
    print("⚙️ Git 자격증명을 시스템에 자동 등록 중...")
    
    # 2. git 자격증명 등록
    try:
        subprocess.run([gh_bin, "auth", "setup-git"], check=True)
    except Exception as e:
        print(f"⚠️ 자격증명 등록 경고: {e}")

    # 3. GitHub 원격 저장소로 첫 푸시
    print("\n🚀 원격 저장소(https://github.com/inarus10/invest.git)로 첫 푸시를 시작합니다...")
    try:
        res = subprocess.run([git_bin, "push", "-u", "origin", "main", "--force"], text=True)
        if res.returncode == 0:
            print("\n" + "=" * 60)
            print("🎉 축하합니다! GitHub 업로드(Push)가 성공적으로 완료되었습니다!")
            print("=" * 60)
            print("\n📌 다음 단계 (GitHub Pages 웹사이트 활성화 - 딱 1회만):")
            print("1. https://github.com/inarus10/invest/settings/pages 접속")
            print("2. Branch를 'main', 폴더를 '/(root)'로 선택 후 [Save] 클릭")
            print("3. 약 1분 후 생성되는 웹 링크:")
            print("   👉 https://inarus10.github.io/invest/\n")
        else:
            print("\n⚠️ 푸시 중 오류가 발생했습니다. 원격 저장소 주소와 권한을 확인해주세요.")
    except Exception as e:
        print(f"\n❌ 푸시 실행 오류: {e}")

if __name__ == "__main__":
    main()
