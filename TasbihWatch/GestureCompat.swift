//
//  GestureCompat.swift
//  سبحة — توافق الإيماءة مع إصدارات watchOS
//
//  تستخدمها الشاشة والودجت. تسمح لك بجعل هدف النشر watchOS 10
//  مع بقاء الإيماءة تعمل على watchOS 11 وما بعده.
//

import SwiftUI

extension View {

    /// الإجراء الرئيسي: «الضغط مرة واحدة (نقرتان متلاحقتان) بالإصبعين» يزيد الذكر.
    ///
    /// `enabled: false` تُعطّل الإيماءة — نستخدمها عندما تكون القائمة المنسدلة مفتوحة
    /// حتى لا يعدّ المستخدم أذكارًا وهو يتنقّل في الإعدادات.
    @ViewBuilder
    func primaryTapShortcut(enabled: Bool = true) -> some View {
        if #available(watchOS 11.0, *) {
            self.handGestureShortcut(.primaryAction, isEnabled: enabled)
        } else {
            self
        }
    }

    /// إجراء ثانوي: يظهر كخيار إضافي لإيماءة الضغط المزدوج.
    /// استخدمه مع زر واحد فقط في الشاشة (زر التصفير مثلًا).
    @ViewBuilder
    func secondaryTapShortcut(enabled: Bool = true) -> some View {
        if #available(watchOS 11.0, *) {
            self.handGestureShortcut(.gestureButton, isEnabled: enabled)
        } else {
            self
        }
    }
}
