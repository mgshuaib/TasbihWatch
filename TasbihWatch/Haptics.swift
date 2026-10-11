//
//  Haptics.swift
//  سبحة — طبقة الاهتزازات
//
//  أضِف هذا الملف إلى هدف التطبيق فقط.
//

import WatchKit

enum Haptics {

    static func play(_ type: WKHapticType) {
        // أبل تتجاهل الاهتزازات المتلاحقة السريعة؛ اهتزاز واحد لكل حدث.
        WKInterfaceDevice.current().play(type)
    }

    /// اهتزاز عادي عند تسجيل ذكر.
    static func tick() { play(.click) }

    /// اكتمال ذكر واحد (٣٣ أو ١٠٠…) — يماثل الوصول لحبّة مميّزة في المسبحة.
    static func roundComplete() { play(.notification) }

    /// الانتقال إلى الذكر التالي — إشارة مختلفة تُشعر المستخدم بتغيّر الذكر بلا نظر.
    static func dhikrChanged() { play(.start) }

    /// 🎉 إتمام المجموعة كلها — إشارتان متعاقبتان لا تخطئهما الأذن.
    static func setCompleted() {
        play(.success)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.55) { play(.success) }
    }

    /// تصفير.
    static func reset() { play(.stop) }
}
